import os
import glob
import numpy as np
import random
from tqdm import tqdm

# Easily editable parameters
L_MAX = 0.005  # Global maximum pipe length
R_MAX = 0.0005  # Global maximum pipe radius
MAX_DEPTH = 5  # Maximum depth of the pipe network
MAX_CHILDREN = 4  # Maximum number of children per pipe
DATA_PATH = "/Users/daghanerdonmez/Desktop/molecular-simulation/molecular-simulation/build/output/outputs"  # Path to the directory containing run folders
TRAIN_RATIO = 0.7  # Ratio of data for training
VAL_RATIO = 0.15  # Ratio of data for validation
TEST_RATIO = 0.15  # Ratio of data for testing
SEED = 42  # Random seed for reproducibility

def read_time_series_from_file(filename):
    """Read the time series data from a receiver file."""
    with open(filename, 'r') as file:
        # Skip the first line
        file.readline()
        # Read the second line (pipe info)
        pipe_info = file.readline().strip()
        # Read the third line (time series)
        time_series = file.readline().strip()
    
    # Convert comma-separated string to list of integers
    if ',' in time_series:
        integer_list = [int(x) for x in time_series.split(',')]
    else:
        # Handle space-separated format if needed
        integer_list = [int(x) for x in time_series.split()]
    
    return pipe_info, integer_list

def compress_time_series(time_series, factor=10):
    """Compress time series by summing every N elements."""
    compressed = []
    for i in range(0, len(time_series), factor):
        chunk = time_series[i:i+factor]
        compressed.append(sum(chunk))
    return compressed

def get_t_peak_normalized(time_series):
    """Get the normalized time index of peak value."""
    if not time_series or max(time_series) == 0:
        return 0
    
    t_peak = np.argmax(time_series)
    t_total = len(time_series)
    return t_peak / t_total if t_total > 0 else 0

def process_run_folder(run_folder, L_MAX, R_MAX, max_pipes=None, verbose=False):
    """Process a single run folder and extract features for all pipes."""
    # Calculate max tensor size based on MAX_DEPTH and MAX_CHILDREN if not provided
    if max_pipes is None:
        max_pipes = sum(MAX_CHILDREN**i for i in range(MAX_DEPTH+1))  # For depth 5, 4 children: 1+4+16+64+256+1024 = 1365
    # Initialize feature tensor with mask=1 (all slots empty initially)
    features = np.ones((max_pipes, 7), dtype=np.float32)  # 7 features per pipe
    
    # Dictionary to map pipe names to slots
    pipe_to_slot = {}
    
    # For verbose output
    if verbose:
        print(f"\n{'='*80}")
        print(f"DETAILED ANALYSIS OF RUN FOLDER: {os.path.basename(run_folder)}")
        print(f"{'='*80}")
    
    # Find all pipe folders
    pipe_folders = [f for f in os.listdir(run_folder) 
                   if os.path.isdir(os.path.join(run_folder, f)) and f.startswith('pipe')]
    
    # Read targetOutput.txt to find emitter pipe and z position
    target_file = os.path.join(run_folder, "targetOutput.txt")
    emitter_pipe = None
    emitter_z = 0
    if os.path.exists(target_file):
        with open(target_file, 'r') as file:
            content = file.read().strip()
            parts = content.split()
            if len(parts) >= 3:
                emitter_pipe = parts[0]  # The pipe name already includes 'pipe' prefix
                emitter_z = float(parts[2])  # z position
    
    # Process each pipe folder
    for pipe_folder_name in pipe_folders:
        pipe_path = os.path.join(run_folder, pipe_folder_name)
        
        # Read simulation_data.txt
        sim_data_file = os.path.join(pipe_path, "simulation_data.txt")
        if not os.path.exists(sim_data_file):
            if verbose:
                print(f"Skipping {pipe_folder_name}: No simulation_data.txt found")
            continue
        
        with open(sim_data_file, 'r') as file:
            sim_data = file.readline().strip().split()
            if len(sim_data) < 5:
                continue
            
            pipe_name = sim_data[0]
            parent_name = sim_data[1]
            length = float(sim_data[2])
            radius = float(sim_data[3])
        
        # Extract pipe number from pipe name (e.g., "pipe597" -> 597)
        try:
            pipe_number = int(pipe_name.replace("pipe", ""))
            
            # Assign slot based on pipe number
            slot = pipe_number
            
            # Skip if the slot is out of range
            if slot >= max_pipes:
                if verbose:
                    print(f"Skipping {pipe_name}: Slot {slot} exceeds max_pipes {max_pipes}")
                continue
                
            # Map pipe name to its slot
            pipe_to_slot[pipe_name] = slot
        except ValueError:
            if verbose:
                print(f"Skipping {pipe_name}: Could not extract valid pipe number")
            continue
        
        # Calculate depth (hops from root)
        depth = 0
        current_pipe = pipe_name
        visited = set()
        
        while current_pipe != "-1" and current_pipe not in visited:
            visited.add(current_pipe)
            depth += 1
            
            # Find parent pipe's data
            parent_folder = f"pipe{current_pipe}"
            if parent_folder == pipe_folder_name:  # We're already in this folder
                current_pipe = parent_name
            else:
                parent_path = os.path.join(run_folder, f"pipe{current_pipe}")
                if os.path.exists(parent_path):
                    parent_sim_file = os.path.join(parent_path, "simulation_data.txt")
                    if os.path.exists(parent_sim_file):
                        with open(parent_sim_file, 'r') as file:
                            parent_data = file.readline().strip().split()
                            if len(parent_data) >= 2:
                                current_pipe = parent_data[1]
                            else:
                                current_pipe = "-1"
                    else:
                        current_pipe = "-1"
                else:
                    current_pipe = "-1"
        
        # Count children
        num_children = 0
        for other_pipe_path in glob.glob(os.path.join(run_folder, "pipe*")):
            other_sim_file = os.path.join(other_pipe_path, "simulation_data.txt")
            if os.path.exists(other_sim_file):
                with open(other_sim_file, 'r') as file:
                    other_data = file.readline().strip().split()
                    if len(other_data) >= 2 and other_data[1] == pipe_name:
                        num_children += 1
        
        # Check for receiver files
        has_receiver = 0
        t_peak = 0
        receiver_files = glob.glob(os.path.join(pipe_path, "#*Ring*.txt"))
        
        for receiver_file in receiver_files:
            with open(receiver_file, 'r') as file:
                first_line = file.readline().strip()
                if first_line == "0":  # Absorbing receiver
                    has_receiver = 1
                    # Read time series data
                    _, time_series = read_time_series_from_file(receiver_file)
                    # Compress time series
                    compressed_series = compress_time_series(time_series)
                    # Get t_peak
                    t_peak = get_t_peak_normalized(compressed_series)
                    break
        
        # Populate feature vector
        features[slot, 0] = length / L_MAX  # Normalized length
        features[slot, 1] = radius / R_MAX  # Normalized radius
        features[slot, 2] = min(depth, MAX_DEPTH) / MAX_DEPTH  # Normalized depth
        features[slot, 3] = min(num_children, MAX_CHILDREN) / MAX_CHILDREN  # Normalized number of children
        features[slot, 4] = has_receiver  # has_receiver
        features[slot, 5] = t_peak  # t_peak
        features[slot, 6] = 0  # mask=0 means pipe exists
        
        if verbose:
            print(f"\nPipe: {pipe_name} (Slot {slot})")
            print(f"  Parent: {parent_name}")
            print(f"  Raw length: {length:.6f}, Normalized: {length / L_MAX:.6f}")
            print(f"  Raw radius: {radius:.6f}, Normalized: {radius / R_MAX:.6f}")
            print(f"  Depth: {depth}, Normalized: {min(depth, MAX_DEPTH) / MAX_DEPTH:.6f}")
            print(f"  Children: {num_children}, Normalized: {min(num_children, MAX_CHILDREN) / MAX_CHILDREN:.6f}")
            print(f"  Has receiver: {has_receiver}")
            print(f"  t_peak: {t_peak:.6f}")
            print(f"  Mask: 0 (pipe exists)")
    
    # Create labels
    y_pipe_slot = -1
    y_z_norm = 0
    
    if emitter_pipe:
        if emitter_pipe in pipe_to_slot:
            y_pipe_slot = pipe_to_slot[emitter_pipe]
            y_z_norm = emitter_z / L_MAX  # Normalize z position
            
            if verbose:
                print(f"\nEMITTER INFORMATION:")
                print(f"  Emitter pipe: {emitter_pipe} (Slot {y_pipe_slot})")
                print(f"  Raw z position: {emitter_z:.6f}, Normalized: {y_z_norm:.6f}")
        else:
            if verbose:
                print(f"\nEMITTER INFORMATION:")
                print(f"  WARNING: Emitter pipe {emitter_pipe} not found in processed pipes!")
                print(f"  This sample will have y_pipe_slot = -1")
    
    if verbose:
        # Print summary statistics
        active_pipes = np.sum(features[:, 6] == 0)
        pipes_with_receivers = np.sum((features[:, 4] == 1) & (features[:, 6] == 0))
        
        print(f"\nSUMMARY STATISTICS:")
        print(f"  Total pipes in run: {active_pipes} out of {max_pipes} slots")
        print(f"  Pipes with receivers: {pipes_with_receivers}")
        print(f"  Feature tensor shape: {features.shape}")
        
        # Print a sample of the feature tensor (first 5 active pipes)
        active_indices = np.where(features[:, 6] == 0)[0]
        if len(active_indices) > 0:
            print(f"\nSAMPLE OF FEATURE TENSOR (first 5 active pipes):")
            sample_size = min(5, len(active_indices))
            for i in range(sample_size):
                idx = active_indices[i]
                print(f"  Pipe at slot {idx}: {features[idx]}")
                print(f"    [length_norm, radius_norm, depth_norm, num_children_norm, has_receiver, t_peak, mask]")
        
        print(f"\nLABELS:")
        print(f"  y_pipe_slot: {y_pipe_slot}")
        print(f"  y_z_norm: {y_z_norm:.6f}")
        print(f"{'='*80}\n")
    
    return features, y_pipe_slot, y_z_norm, pipe_to_slot

def process_data(data_path, L_MAX, R_MAX, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42):
    """Process all run folders and create train/val/test splits."""
    random.seed(seed)
    
    # Find all run folders
    run_folders = [os.path.join(data_path, f) for f in os.listdir(data_path) 
                  if os.path.isdir(os.path.join(data_path, f)) and not f.startswith('.')]
    
    # Shuffle run folders for random splitting
    random.shuffle(run_folders)
    
    # Calculate split indices
    n_runs = len(run_folders)
    n_train = int(n_runs * train_ratio)
    n_val = int(n_runs * val_ratio)
    
    # Split run folders
    train_folders = run_folders[:n_train]
    val_folders = run_folders[n_train:n_train+n_val]
    test_folders = run_folders[n_train+n_val:]
    
    print(f"Total runs: {n_runs}")
    print(f"Training runs: {len(train_folders)}")
    print(f"Validation runs: {len(val_folders)}")
    print(f"Test runs: {len(test_folders)}")
    
    # Process each split
    train_data = process_split(train_folders, "train", L_MAX, R_MAX)
    val_data = process_split(val_folders, "val", L_MAX, R_MAX)
    test_data = process_split(test_folders, "test", L_MAX, R_MAX)
    
    # Save all data to a single npz file
    output_file = os.path.join(data_path, "pipe_network_data.npz")
    np.savez_compressed(
        output_file,
        train_features=train_data['features'],
        train_pipe_labels=train_data['pipe_labels'],
        train_z_labels=train_data['z_labels'],
        val_features=val_data['features'],
        val_pipe_labels=val_data['pipe_labels'],
        val_z_labels=val_data['z_labels'],
        test_features=test_data['features'],
        test_pipe_labels=test_data['pipe_labels'],
        test_z_labels=test_data['z_labels']
    )
    
    print(f"Data saved to {output_file}")
    
    # Print dataset statistics
    print("\nDataset statistics:")
    print(f"Training samples: {len(train_data['features'])}")
    print(f"Validation samples: {len(val_data['features'])}")
    print(f"Test samples: {len(test_data['features'])}")
    
    # Print label statistics
    if len(train_data['features']) > 0:
        valid_labels = np.sum(train_data['pipe_labels'] >= 0)
        print(f"Training samples with valid emitter pipe labels: {valid_labels} ({valid_labels/len(train_data['features'])*100:.1f}%)")
    
    return output_file

def process_split(folders, split_name, L_MAX, R_MAX):
    """Process a list of run folders for a specific data split."""
    features_list = []
    pipe_labels = []
    z_labels = []
    
    print(f"Processing {split_name} split...")
    for i, folder in enumerate(tqdm(folders)):
        try:
            # Print detailed info only for the first folder in the first split
            verbose = (i == 0 and split_name == "train") or (i == 0 and split_name == "test" and not folders)
            features, y_pipe_slot, y_z_norm, _ = process_run_folder(folder, L_MAX, R_MAX, max_pipes=None, verbose=verbose)
            
            # Include all samples, even if emitter pipe wasn't found
            features_list.append(features)
            pipe_labels.append(y_pipe_slot)
            z_labels.append(y_z_norm)
        except Exception as e:
            print(f"Error processing {folder}: {e}")
    
    # Convert lists to numpy arrays
    if features_list:
        features_array = np.stack(features_list)
        pipe_labels_array = np.array(pipe_labels)
        z_labels_array = np.array(z_labels)
    else:
        # Create empty arrays with correct shape if no valid samples
        max_pipes = sum(MAX_CHILDREN**i for i in range(MAX_DEPTH+1))
        features_array = np.zeros((0, max_pipes, 7), dtype=np.float32)
        pipe_labels_array = np.zeros(0, dtype=np.int32)
        z_labels_array = np.zeros(0, dtype=np.float32)
    
    return {
        'features': features_array,
        'pipe_labels': pipe_labels_array,
        'z_labels': z_labels_array
    }

def calculate_global_max_values(data_path):
    """Calculate global maximum length and radius across all runs."""
    print("Calculating global maximum length and radius...")
    max_length = 0
    max_radius = 0
    
    # Find all run folders
    run_folders = [os.path.join(data_path, f) for f in os.listdir(data_path) 
                  if os.path.isdir(os.path.join(data_path, f)) and not f.startswith('.')]
    
    for run_folder in tqdm(run_folders):
        pipe_folders = [f for f in os.listdir(run_folder) 
                       if os.path.isdir(os.path.join(run_folder, f)) and f.startswith('pipe')]
        
        for pipe_folder_name in pipe_folders:
            pipe_path = os.path.join(run_folder, pipe_folder_name)
            sim_data_file = os.path.join(pipe_path, "simulation_data.txt")
            
            if os.path.exists(sim_data_file):
                with open(sim_data_file, 'r') as file:
                    sim_data = file.readline().strip().split()
                    if len(sim_data) >= 4:
                        length = float(sim_data[2])
                        radius = float(sim_data[3])
                        max_length = max(max_length, length)
                        max_radius = max(max_radius, radius)
    
    print(f"Global maximum length: {max_length}")
    print(f"Global maximum radius: {max_radius}")
    
    return max_length, max_radius

if __name__ == "__main__":
    # Use the global parameters defined at the top of the file
    # If you want to calculate L_MAX and R_MAX from data instead of using the predefined values,
    # uncomment the following lines:
    # print("Calculating L_MAX and R_MAX from data...")
    # L_MAX, R_MAX = calculate_global_max_values(DATA_PATH)
    
    # Calculate max tensor size based on MAX_DEPTH and MAX_CHILDREN
    max_pipes = sum(MAX_CHILDREN**i for i in range(MAX_DEPTH+1))
    print(f"Maximum number of pipes: {max_pipes} (depth={MAX_DEPTH}, children={MAX_CHILDREN})")
    
    # Process data and create train/val/test splits
    output_file = process_data(
        DATA_PATH, 
        L_MAX, 
        R_MAX,
        TRAIN_RATIO,
        VAL_RATIO,
        TEST_RATIO,
        SEED
    )
    
    print(f"\nProcessing complete. Data saved to {output_file}")
