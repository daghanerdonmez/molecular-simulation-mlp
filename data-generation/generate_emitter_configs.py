import random
import math
import yaml
import os
from pathlib import Path

def add_random_emitter_to_config(base_config_path, output_path, config_index):
    """
    Load a base network configuration YAML, add a random emitter to one
    of the pipes, and save the modified configuration to a new file.
    
    Parameters:
    -----------
    base_config_path : str
        Path to the base network configuration YAML file.
    output_path : str
        Directory path to save the modified configuration.
    config_index : int
        Index to use in the output file name.
    """
    # Load the base YAML configuration
    with open(base_config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Get list of pipe names
    pipe_names = list(config['pipes'].keys())
    
    # Randomly select a pipe
    selected_pipe_name = random.choice(pipe_names)
    selected_pipe = config['pipes'][selected_pipe_name]
    
    # Get pipe dimensions for emitter placement constraints
    pipe_radius = selected_pipe['radius']
    pipe_length = selected_pipe['length']
    
    # Create a random emitter
    # Random position within the pipe
    z = random.uniform(-0.9 * pipe_length, 0.9 * pipe_length)
    r = random.uniform(0.1 * pipe_radius, 0.9 * pipe_radius)
    theta = random.uniform(0, 2 * math.pi)
    
    # Random particle count between 1000-2000
    particle_count = random.randint(1000, 2000)
    
    # Create emitter data structure
    emitter_data = {
        'z': z,
        'r': r,
        'theta': theta,
        'emitter_pattern': str(particle_count),
        'emitter_pattern_type': 'complete'
    }
    
    # Add the emitter to the selected pipe
    # If the 'emitters' key doesn't exist, create it
    if 'emitters' not in selected_pipe:
        selected_pipe['emitters'] = []
    
    # Add the emitter to the pipe
    selected_pipe['emitters'].append(emitter_data)
    
    # Save the modified configuration
    output_file_path = os.path.join(output_path, f"network_config_{config_index}.yaml")
    with open(output_file_path, 'w') as file:
        yaml.dump(config, file, sort_keys=False)
    
    print(f"Generated configuration {config_index}: Emitter added to {selected_pipe_name}")

def generate_multiple_configs(base_config_path, output_dir, count=1000):
    """
    Generate multiple network configurations with random emitters.
    
    Parameters:
    -----------
    base_config_path : str
        Path to the base network configuration YAML file.
    output_dir : str
        Directory to save the generated configurations.
    count : int
        Number of configurations to generate.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate the specified number of configurations
    for i in range(count):
        add_random_emitter_to_config(base_config_path, output_dir, i)
        
    print(f"Successfully generated {count} network configurations with random emitters.")

if __name__ == "__main__":
    # Define paths
    script_dir = Path(__file__).parent.absolute()
    base_config_path = os.path.join(script_dir, "network_config.yaml")
    output_dir = os.path.join(script_dir, "configs_2")
    
    # Generate 1000 configurations
    generate_multiple_configs(base_config_path, output_dir, count=1000)
