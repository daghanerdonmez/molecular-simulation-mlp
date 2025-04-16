import os
import shutil
import glob
import numpy as np
from scipy import stats

dt = 0.01
total_time = 500

def read_integers_from_file(filename):
    """Read the second line from a file and convert it to a list of integers."""
    with open(filename, 'r') as file:
        # Skip the first line
        first_line = file.readline()
        # Read the second line
        data = file.readline()
    
    # Convert comma-separated string to list of integers
    integer_list = [int(x) for x in data.strip().split(',')]
    return first_line, integer_list

def calculate_statistics(arr):
    """Calculate various statistics for the array."""
    # Convert to numpy array for easier calculations
    arr = np.array(arr)
    
    # Find first non-zero index
    nonzero_indices = np.nonzero(arr)[0]
    first_nonzero_index = nonzero_indices[0] if len(nonzero_indices) > 0 else -1
    
    # Find max value and its index
    max_value = np.max(arr)
    max_index = np.argmax(arr)
    
    # Calculate sum, mean, and std
    total_sum = np.sum(arr)
    mean = np.mean(arr)
    std = np.std(arr)
    
    # Calculate skewness
    skewness = stats.skew(arr) if len(arr) > 2 else 0
    
    return {
        'first_nonzero_time': first_nonzero_index*dt,
        'max_value': max_value,
        'max_time': max_index*dt,
        'total_sum': total_sum,
        'mean': mean,
        'std': std,
        'skewness': skewness
    }

def process_receiver_files(source_path):
    """Process all receiver files in the Outputs directory structure."""
    # Copy the Outputs directory to the current directory
    local_outputs_dir = os.path.join(os.getcwd(), "Outputs_Copy")
    
    # Remove existing copy if it exists
    if os.path.exists(local_outputs_dir):
        shutil.rmtree(local_outputs_dir)
    
    # Copy the directory
    print(f"Copying {source_path} to {local_outputs_dir}...")
    shutil.copytree(source_path, local_outputs_dir)
    
    # Process all run folders
    run_folders = [f for f in os.listdir(local_outputs_dir) 
                  if os.path.isdir(os.path.join(local_outputs_dir, f)) and not f.startswith('.')]
    
    results = {}
    
    for run_folder in run_folders:
        run_path = os.path.join(local_outputs_dir, run_folder)
        results[run_folder] = {}
        
        # Process all pipe folders
        pipe_folders = [f for f in os.listdir(run_path) 
                       if os.path.isdir(os.path.join(run_path, f))]
        
        for pipe_folder in pipe_folders:
            pipe_path = os.path.join(run_path, pipe_folder)
            results[run_folder][pipe_folder] = {}
            
            # Find all receiver files (starting with #)
            receiver_files = glob.glob(os.path.join(pipe_path, "#*.txt"))
            
            for receiver_file in receiver_files:
        
                file_name = os.path.basename(receiver_file)
                
                try:
                    # Read data from the file
                    first_line, integer_list = read_integers_from_file(receiver_file)
                    first_line_list = first_line.split()
                    first_line_list[0] = first_line_list[0].strip("pipe")
                    first_line_list[0] = first_line_list[0].split("-")[0]
                    first_line = " ".join(first_line_list)
                    first_line += "\n"
                    
                    # Calculate statistics
                    stats = calculate_statistics(integer_list)
                    
                    # Store the results
                    results[run_folder][pipe_folder][file_name] = stats
                    
                    # Format statistics as a string
                    stats_str = (
                        f"{stats['first_nonzero_time']}, "
                        f"{stats['max_value']}, "
                        f"{stats['max_time']}, " 
                        f"{stats['total_sum']}, "
                        f"{stats['mean']:.4f}, "
                        f"{stats['std']:.4f}, "
                        f"{stats['skewness']:.4f}"
                    )
                    
                    # Write statistics back to the file
                    with open(receiver_file, 'w') as file:
                        file.write(first_line)  # Write the first line back
                        file.write(stats_str)   # Write statistics
                    
                    print(f"Processed: {run_folder}/{pipe_folder}/{file_name}")
                    print(f"  Statistics: {stats_str}")
                except Exception as e:
                    print(f"Error processing {receiver_file}: {e}")

            # Find all the simulation_data files
            simulation_data_files = glob.glob(os.path.join(pipe_path, "simulation_data.txt"))

            for simulation_data_file in simulation_data_files:
                file_name = os.path.basename(simulation_data_file)

                # If the second word of the first line is none, change it to -1
                with open(simulation_data_file, 'r') as file:
                    first_line = file.readline()
                    first_line_list = first_line.split()
                    if first_line_list[1] == "none":
                        first_line_list[1] = "-1"
                        first_line = " ".join(first_line_list)
                        first_line += "\n"
                    else:
                        # The second word is in the format pipex-y
                        # Change it to x
                        first_line_list[1] = first_line_list[1].split("-")[0]
                        first_line_list[1] = first_line_list[1].strip("pipe")
                        first_line = " ".join(first_line_list)
                        first_line += "\n"
                    
                    # Do the same to the first word
                    first_line_list[0] = first_line_list[0].split("-")[0]
                    first_line_list[0] = first_line_list[0].strip("pipe")
                    first_line = " ".join(first_line_list)
                    first_line += "\n"

                # Write back to the file
                with open(simulation_data_file, 'w') as file:
                    file.write(first_line)

    return results

if __name__ == "__main__":
    # Path to the Outputs directory
    source_path = "/Users/daghanerdonmez/Desktop/molecular-simulation/molecular-simulation/src/output/Outputs"
    
    # Process all receiver files
    results = process_receiver_files(source_path)
    
    # Print summary
    print("\nProcessing Summary:")
    for run, pipes in results.items():
        print(f"Run: {run}")
        for pipe, files in pipes.items():
            print(f"  Pipe: {pipe}")
            for file, stats in files.items():
                print(f"    File: {file}")
                for stat_name, stat_value in stats.items():
                    if isinstance(stat_value, float):
                        print(f"      {stat_name}: {stat_value:.4f}")
                    else:
                        print(f"      {stat_name}: {stat_value}")
