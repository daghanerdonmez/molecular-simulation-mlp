import os
import shutil
import glob
import random

def process_data_for_training(source_dir, target_dir, validation_dir=None, validation_split=0.25):
    """
    Process data from Outputs_Copy directory to create training data in the specified format.
    
    Args:
        source_dir: Path to the Outputs_Copy directory
        target_dir: Path to create the train-data directory
        validation_dir: Path to create the validation-data directory (if None, no validation data is created)
        validation_split: Fraction of data to use for validation (default: 0.25)
    """
    # Create the target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Create validation directory if specified
    if validation_dir and not os.path.exists(validation_dir):
        os.makedirs(validation_dir)
    
    # Get all run folders (they are named with timestamps)
    run_folders = [f for f in os.listdir(source_dir) 
                  if os.path.isdir(os.path.join(source_dir, f)) and not f.startswith('.')]
    
    # Randomly shuffle the run folders
    random.shuffle(run_folders)
    
    # Split the run folders into training and validation sets
    split_idx = int(len(run_folders) * (1 - validation_split))
    train_folders = run_folders[:split_idx]
    val_folders = run_folders[split_idx:]
    
    print(f"Total run folders: {len(run_folders)}")
    print(f"Training run folders: {len(train_folders)} ({len(train_folders)/len(run_folders)*100:.1f}%)")
    print(f"Validation run folders: {len(val_folders)} ({len(val_folders)/len(run_folders)*100:.1f}%)")
    
    # Process training data
    process_run_folders(source_dir, target_dir, train_folders)
    
    # Process validation data if validation directory is specified
    if validation_dir:
        process_run_folders(source_dir, validation_dir, val_folders)
    
    print(f"Processing complete.")
    print(f"Training data created in {target_dir}")
    if validation_dir:
        print(f"Validation data created in {validation_dir}")

def process_run_folders(source_dir, target_dir, run_folders):
    """
    Process the specified run folders and create the formatted data files.
    
    Args:
        source_dir: Path to the source directory containing run folders
        target_dir: Path to the target directory to create formatted data
        run_folders: List of run folder names to process
    """
    for run_folder in run_folders:
        source_run_path = os.path.join(source_dir, run_folder)
        target_run_path = os.path.join(target_dir, run_folder)
        
        # Create directory for this run
        if not os.path.exists(target_run_path):
            os.makedirs(target_run_path)
        
        # 1. Copy network_data.txt to meta.txt
        network_data_path = os.path.join(source_run_path, "network_data.txt")
        meta_path = os.path.join(target_run_path, "meta.txt")
        if os.path.exists(network_data_path):
            shutil.copy2(network_data_path, meta_path)
            print(f"Created meta.txt for {run_folder}")
        
        # 2. Create pipes.txt by concatenating all simulation_data.txt files
        pipes_path = os.path.join(target_run_path, "pipes.txt")
        with open(pipes_path, 'w') as pipes_file:
            # Get all pipe folders
            pipe_folders = [f for f in os.listdir(source_run_path) 
                           if os.path.isdir(os.path.join(source_run_path, f)) and f.startswith('pipe')]
            
            # Sort pipe folders numerically
            pipe_folders.sort(key=lambda x: int(x.replace('pipe', '')))
            
            for i, pipe_folder in enumerate(pipe_folders):
                pipe_path = os.path.join(source_run_path, pipe_folder)
                sim_data_path = os.path.join(pipe_path, "simulation_data.txt")
                
                if os.path.exists(sim_data_path):
                    with open(sim_data_path, 'r') as sim_file:
                        content = sim_file.read().strip()
                        pipes_file.write(content)
                        # Add newline between pipe data, but not after the last one
                        if i < len(pipe_folders) - 1:
                            pipes_file.write('\n')
            
            print(f"Created pipes.txt for {run_folder}")
        
        # 3. Create receivers.txt with all receiver data in one-row-per-receiver format
        receivers_path = os.path.join(target_run_path, "receivers.txt")
        with open(receivers_path, 'w') as receivers_file:
            # Get all pipe folders
            pipe_folders = [f for f in os.listdir(source_run_path) 
                           if os.path.isdir(os.path.join(source_run_path, f)) and f.startswith('pipe')]
            
            # Sort pipe folders numerically
            pipe_folders.sort(key=lambda x: int(x.replace('pipe', '')))
            
            for pipe_folder in pipe_folders:
                pipe_path = os.path.join(source_run_path, pipe_folder)
                
                # Find all receiver files (starting with #)
                receiver_files = glob.glob(os.path.join(pipe_path, "#*.txt"))
                
                # Sort receiver files by their number
                receiver_files.sort(key=lambda x: int(os.path.basename(x).split('-')[0].replace('#', '')))
                
                for receiver_file in receiver_files:
                    with open(receiver_file, 'r') as rec_file:
                        # Skip the first line (header)
                        first_line = rec_file.readline()
                        # Read the second line (data)
                        second_line = rec_file.readline().strip()
                        # Convert comma-separated string to list of values
                        values = first_line.split(' ') + second_line.split(',')
                        # Replace -0.01 with -1
                        values = [float(x) if x != '-0.01' else -1 for x in values]
                        # Write the each receiver data as a single row
                        receivers_file.write(' '.join(map(str, values)) + '\n')
            
            print(f"Created receivers.txt for {run_folder}")
        
        # 4. Copy targetOutput.txt to target.txt
        target_output_path = os.path.join(source_run_path, "targetOutput.txt")
        target_path = os.path.join(target_run_path, "target.txt")
        if os.path.exists(target_output_path):
            shutil.copy2(target_output_path, target_path)
            print(f"Created target.txt for {run_folder}")

if __name__ == "__main__":
    # Path to the Outputs_Copy directory
    source_dir = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/Outputs_Copy"
    
    # Path to create the train-data directory
    target_dir = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/train-data"
    
    # Path to create the validation-data directory
    validation_dir = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/validation-data"
    
    # Process the data with 75% for training and 25% for validation
    process_data_for_training(source_dir, target_dir, validation_dir, validation_split=0.25)