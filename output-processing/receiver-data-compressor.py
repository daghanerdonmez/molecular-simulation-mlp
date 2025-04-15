import os
import shutil
import glob

def read_integers_from_file(filename):
    """Read the second line from a file and convert it to a list of integers."""
    with open(filename, 'r') as file:
        # Skip the first line
        file.readline()
        # Read the second line
        data = file.readline()
    
    # Convert comma-separated string to list of integers
    integer_list = [int(x) for x in data.strip().split(',')]
    return integer_list

def compress_data(arr, compression_rate):
    """Compress an array by summing groups of 'compression_rate' elements."""
    new_counters = []
    counter = 0
    current_sum = 0
    n = len(arr)
    
    for i in range(n):
        if counter % compression_rate == 0 and counter != 0:
            new_counters.append(current_sum)
            current_sum = 0
        current_sum += arr[i]
        counter += 1
    
    # Add the last group if there's any remaining data
    if current_sum > 0:
        new_counters.append(current_sum)
    
    return new_counters

def process_receiver_files(source_path, compression_rate=100):
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
                    # Read and compress the data
                    integer_list = read_integers_from_file(receiver_file)
                    compressed_data = compress_data(integer_list, compression_rate)
                    
                    # Store the results
                    results[run_folder][pipe_folder][file_name] = compressed_data
                    
                    # Write compressed data back to the file
                    with open(receiver_file, 'r') as file:
                        first_line = file.readline()  # Save the first line
                    
                    # Write back to the file
                    with open(receiver_file, 'w') as file:
                        file.write(first_line)  # Write the first line back
                        file.write(','.join(map(str, compressed_data)))  # Write compressed data
                    
                    print(f"Processed: {run_folder}/{pipe_folder}/{file_name}")
                    print(f"  Original length: {len(integer_list)}")
                    print(f"  Compressed length: {len(compressed_data)}")
                    print(f"  Compressed data written back to file")
                except Exception as e:
                    print(f"Error processing {receiver_file}: {e}")
    
    return results

if __name__ == "__main__":
    # Path to the Outputs directory
    source_path = "/Users/daghanerdonmez/Desktop/molecular-simulation/molecular-simulation/src/output/Outputs"
    
    # Compression rate
    compression_rate = 1000
    
    # Process all receiver files
    results = process_receiver_files(source_path, compression_rate)
    
    # Print summary
    print("\nProcessing Summary:")
    for run, pipes in results.items():
        print(f"Run: {run}")
        for pipe, files in pipes.items():
            print(f"  Pipe: {pipe}")
            for file, data in files.items():
                print(f"    File: {file}, Compressed data length: {len(data)}")
