import random
import math
import yaml

def generate_pipe_tree_yaml(
    max_branches=4,
    max_depth=5,
    min_pipe_radius=0.0001, 
    max_pipe_radius=0.001,
    min_pipe_length=0.0001, 
    max_pipe_length=0.001,
    flow_value=0.0001,
    min_particle_count=1000,
    max_particle_count=5000,
    receiver_thickness=0.0005
):
    """
    Generates a tree-structured network of pipes with ring receivers at leaf nodes.
    
    Parameters:
    -----------
    max_branches : int
        Maximum number of branches a pipe can have (0-4)
    max_depth : int
        Maximum depth of the tree structure
    min_pipe_radius, max_pipe_radius : float
        Range for the pipe radius
    min_pipe_length, max_pipe_length : float
        Range for the pipe length
    flow_value : float
        The flow value to assign to the root pipe
    min_particle_count, max_particle_count : int
        Range for the single emitter pattern (stored as a string)
        
    Returns:
    --------
    A YAML-formatted string describing the generated structure
    """

    # -------------------------------
    # 1) Initialize the tree with a root pipe
    # -------------------------------
    pipes = []
    
    # Function to calculate slot ID based on level and branch index
    def slot_id(level, branch_idx):
        # Use max_branches instead of hardcoded 4
        return (max_branches**level - 1)//(max_branches - 1) + branch_idx   # geometric sum
    
    # Create the root pipe (always slot 0)
    root_pipe = {
        'name': f"pipe0",  # Root is always pipe0
        'length': random.uniform(min_pipe_length, max_pipe_length),
        'radius': random.uniform(min_pipe_radius, max_pipe_radius),
        'left_connections': [],
        'right_connections': [],
        'flow': flow_value,
        'emitters': [],
        'receivers': [],
        'depth': 0,
        'slot': 0  # Track the slot ID
    }
    pipes.append(root_pipe)
    
    # -------------------------------
    # 2) Build the tree structure using BFS
    # -------------------------------
    from collections import deque
    queue = deque([])

    # Generate first level children for root (level 1)
    num_branches_for_root = random.randint(1, max_branches)
    for branch_idx in range(num_branches_for_root):
        # Calculate slot ID for this child
        child_slot = slot_id(1, branch_idx)
        
        child_pipe = {
            'name': f"pipe{child_slot}",
            'length': random.uniform(min_pipe_length, max_pipe_length),
            'radius': random.uniform(min_pipe_radius, max_pipe_radius),
            'left_connections': [root_pipe['name']],
            'right_connections': [],
            'flow': 0,  # Will be calculated later
            'emitters': [],
            'receivers': [],
            'depth': 1,
            'slot': child_slot,
            'parent_slot': 0,  # Root's slot
            'branch_idx': branch_idx  # Which branch of the parent
        }
        
        # Connect parent to child
        root_pipe['right_connections'].append(child_pipe['name'])
        
        # Add child to pipes list and queue
        pipes.append(child_pipe)
        queue.append(child_pipe)
    
    while queue:
        parent_pipe = queue.popleft()
        current_depth = parent_pipe['depth']
        parent_slot = parent_pipe['slot']
        
        # Stop branching if we've reached max depth
        if current_depth >= max_depth:
            continue
        
        # Determine number of branches (0 to max_branches)
        num_branches = random.randint(0, max_branches)
        
        # Create child pipes
        for branch_idx in range(num_branches):
            # Calculate slot ID for this child based on parent's position
            # For each parent slot, we can have up to max_branches children
            # The first child of parent at slot p will be at: max_branches*p + 1
            # The second child will be at: max_branches*p + 2, etc.
            child_slot = slot_id(current_depth + 1, max_branches * (parent_slot - slot_id(current_depth, 0)) + branch_idx)
            
            child_pipe = {
                'name': f"pipe{child_slot}",
                'length': random.uniform(min_pipe_length, max_pipe_length),
                'radius': random.uniform(min_pipe_radius, max_pipe_radius),
                'left_connections': [parent_pipe['name']],
                'right_connections': [],
                'flow': 0,  # Will be calculated later
                'emitters': [],
                'receivers': [],
                'depth': current_depth + 1,
                'slot': child_slot,
                'parent_slot': parent_slot,
                'branch_idx': branch_idx
            }
            
            # Connect parent to child
            parent_pipe['right_connections'].append(child_pipe['name'])
            
            # Add child to pipes list and queue
            pipes.append(child_pipe)
            queue.append(child_pipe)
    
    # -------------------------------
    # 3) Distribute flow values
    # -------------------------------
    # Build a name->pipe mapping for easy lookup
    
    for pipe in pipes:
        pipe['flow'] = flow_value

    #I'VE CHANGED THIS PART SO THAT ALL PIPES HAVE THE SAME FLOW VALUE BECAUSE I THING THE OLD FLOW CALCULATION GIVES NO REAL VALUE
    #TO THE TASK I'M TRYING TO SOLVE RIGHT NOW IT JUST MAKES THE SIMULATION SLOWER

    # -------------------------------
    # 4) Place a single Emitter
    # -------------------------------
    # Choose a pipe for the emitter (prefer pipes closer to root)
    depths = [pipe.get('depth', 0) for pipe in pipes]
    max_tree_depth = max(depths)
    
    # Use exponential decay for weights (higher chance for pipes closer to root)
    alpha = 1.0 / (max_tree_depth + 1) if max_tree_depth > 0 else 1.0
    weights = [math.exp(-alpha * d) for d in depths]
    total_weight = sum(weights)
    norm_weights = [w / total_weight for w in weights]
    
    emitter_pipe_idx = random.choices(range(len(pipes)), weights=norm_weights, k=1)[0]
    emitter_pipe = pipes[emitter_pipe_idx]
    
    # Random emitter position
    z = random.uniform(-0.9 * emitter_pipe['length'], 0.9 * emitter_pipe['length'])
    r = random.uniform(0.1 * emitter_pipe['radius'], 0.9 * emitter_pipe['radius'])
    theta = random.uniform(0, 2 * math.pi)
    
    # Random particle count for emitter pattern
    emitter_pattern_int = random.randint(min_particle_count, max_particle_count)
    
    emitter_data = {
        'z': z,
        'r': r,
        'theta': theta,
        'emitter_pattern': str(emitter_pattern_int),
        'emitter_pattern_type': 'complete'
    }
    emitter_pipe['emitters'].append(emitter_data)

    # -------------------------------
    # 5) Determine leaf pipes and attach sinks and receivers
    # -------------------------------
    sinks = {}
    sink_count = 0
    receiver_id = 1
    
    for pipe in pipes:
        if len(pipe['right_connections']) == 0:
            # This is a leaf pipe, add a sink
            sink_count += 1
            sink_name = f"sink{sink_count}"
            pipe['right_connections'].append(sink_name)
            sinks[sink_name] = {
                'left_connections': [pipe['name']]
            }
            
            # Add a ring receiver with countingType 0 at the end of the leaf pipe
            thickness = receiver_thickness
            receiver_data = {
                'type': 'Ring type with thickness',
                'name': f"#{receiver_id}-Ring type with thickness",
                'z': pipe['length'] - thickness,  # Place it at the end, accounting for thickness
                'countingType': 0,
                'thickness': thickness
            }
            pipe['receivers'].append(receiver_data)
            receiver_id += 1

    # -------------------------------
    # 6) Build final YAML structure
    # -------------------------------
    pipes_dict = {}
    for pipe in pipes:
        pipe_name = pipe['name']
        
        pipe_info = {
            'length': pipe['length'],
            'radius': pipe['radius'],
            'particle_count': 0,
            'left_connections': pipe['left_connections'],
            'right_connections': pipe['right_connections'],
            'flow': pipe['flow']
        }
        
        # Only add emitters if not empty
        if pipe['emitters']:
            pipe_info['emitters'] = pipe['emitters']
            
        # Only add receivers if not empty
        if pipe['receivers']:
            pipe_info['receivers'] = pipe['receivers']
        
        pipes_dict[pipe_name] = pipe_info

    data = {
        'pipes': pipes_dict,
        'sinks': sinks,
        'flow': flow_value
    }

    # Convert to YAML string
    yaml_str = yaml.dump(data, sort_keys=False)
    return yaml_str

def generate_n_times(n):
    """
    Generate n YAML configurations with the specified parameters
    
    Parameters:
    -----------
    n : int
        Number of configurations to generate
    """
    for i in range(n):
        yaml_output = generate_pipe_tree_yaml(
            max_branches=4,
            max_depth=5,
            min_pipe_radius=0.0001,
            max_pipe_radius=0.0005,
            min_pipe_length=0.002,
            max_pipe_length=0.005,
            flow_value=0.0002,
            min_particle_count=1000,
            max_particle_count=2000,
            receiver_thickness=0.0005)
    
        # Save to file
        with open(f"tree_configs/network_config_{i}.yaml", "w") as f:
            f.write(yaml_output)


if __name__ == "__main__":
    # Default: max 4 branches, max depth 5
    generate_n_times(1000)
