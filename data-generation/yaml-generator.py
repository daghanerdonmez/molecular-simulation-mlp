import random
import math
import yaml

def generate_pipe_tree_yaml(
    min_pipe_num=10, 
    max_pipe_num=20,
    min_pipe_radius=0.0001, 
    max_pipe_radius=0.001,
    min_pipe_length=0.0001, 
    max_pipe_length=0.001,
    flow_value=0.0001,
    min_particle_count=1000,
    max_particle_count=5000
):
    """
    Generates a random tree of pipes with optional receivers, a single emitter, and sinks.
    
    Parameters:
    -----------
    min_pipe_num, max_pipe_num : int
        Range for how many pipes will be generated.
    min_receiver_num, max_receiver_num : int
        Range for how many total receivers will be placed among the pipes.
    min_pipe_radius, max_pipe_radius : float
        Range for the pipe radius.
    min_pipe_length, max_pipe_length : float
        Range for the pipe length.
    flow_value : float
        The flow value to assign to every pipe (placeholder usage).
    min_particle_count, max_particle_count : int
        Range for the single emitter pattern (stored as a string).
        
    Returns:
    --------
    A YAML-formatted string describing the generated structure.
    """

    # -------------------------------
    # 1) Determine number of pipes
    # -------------------------------
    pipe_count = random.randint(min_pipe_num, max_pipe_num)

    # Prepare list to hold pipe info (we'll convert it to a dict later)
    # Each entry will be a dict:
    # {
    #   'name': str,
    #   'length': float,
    #   'radius': float,
    #   'left_connections': [ ... ],
    #   'right_connections': [ ... ],
    #   'flow': float,
    #   'emitters': [],
    #   'receivers': []
    # }
    pipes = []
    
    # -------------------------------
    # 2) Generate random length/radius for each pipe
    # -------------------------------
    for i in range(pipe_count):
        pipe_name = f"pipe{i}"  # e.g. "pipe0", "pipe1", ...
        length = random.uniform(min_pipe_length, max_pipe_length)
        radius = random.uniform(min_pipe_radius, max_pipe_radius)
        
        pipe_data = {
            'name': pipe_name,
            'length': length,
            'radius': radius,
            'left_connections': [],
            'right_connections': [],
            'flow': flow_value,  # For now, assign the same flow_value to all pipes
            'emitters': [],
            'receivers': []
        }
        pipes.append(pipe_data)

    # -------------------------------
    # 3) Build a random tree
    # -------------------------------
    # We'll choose one pipe to be the "root" (no left connections).
    # Every other pipe gets exactly one parent, chosen at random among existing pipes,
    # ensuring this forms a valid tree without cycles.
    
    # Pick a random pipe for root
    root_index = random.randint(0, pipe_count - 1)
    # Move root pipe to front if needed (so root is at index 0).
    if root_index != 0:
        pipes[0], pipes[root_index] = pipes[root_index], pipes[0]

    # Shuffle the remaining pipes (indices 1..pipe_count-1)
    non_root_pipes = pipes[1:]
    random.shuffle(non_root_pipes)
    pipes[1:] = non_root_pipes

    # For the remaining pipes (indexes 1..pipe_count-1), assign a parent
    for i in range(1, pipe_count):
        # pick a parent from among [0..i-1]
        parent_index = random.randint(0, i - 1)
        child_index = i
        parent_name = pipes[parent_index]['name']
        child_name = pipes[child_index]['name']
        # Record the connections
        pipes[child_index]['left_connections'].append(parent_name)
        pipes[parent_index]['right_connections'].append(child_name)

    # -------------------------------
    # 3.1) Assign depth to each pipe
    # -------------------------------
    # BFS from root, set depth for each pipe
    name_to_pipe = {pipe['name']: pipe for pipe in pipes}
    pipes[0]['depth'] = 0
    from collections import deque
    queue = deque([pipes[0]])
    while queue:
        parent = queue.popleft()
        parent_depth = parent['depth']
        for child_name in parent['right_connections']:
            if child_name in name_to_pipe:
                child = name_to_pipe[child_name]
                child['depth'] = parent_depth + 1
                queue.append(child)

    # -------------------------------
    # 3.5) Distribute flow values
    # -------------------------------
    # Build a name->pipe mapping for easy lookup
    name_to_pipe = {pipe['name']: pipe for pipe in pipes}
    # Set root flow
    pipes[0]['flow'] = flow_value
    # Traverse tree and assign flows
    from collections import deque
    queue = deque([pipes[0]])
    while queue:
        parent = queue.popleft()
        children_names = parent['right_connections']
        if not children_names:
            continue
        # Get children pipes
        children = [name_to_pipe[name] for name in children_names]
        # Compute sum of r
        radii = [child['radius'] for child in children]
        total_r = sum(radii)
        # Assign flows
        for child, r in zip(children, radii):
            child['flow'] = parent['flow'] * (r / total_r) if total_r > 0 else 0
            queue.append(child)

    # -------------------------------
    # 4) Place Receivers
    # -------------------------------
    # We first determine how many total receivers to place across all pipes
    receiver_count = random.randint(int(0.5 * pipe_count), int(1.5 * pipe_count))
    receiver_id = 1  # to give them distinct names

    for _ in range(receiver_count):
        # pick a random pipe to place this receiver
        pipe_idx = random.randint(0, pipe_count - 1)
        pipe_radius = pipes[pipe_idx]['radius']
        pipe_length = pipes[pipe_idx]['length']
        
        # random position (z, r, theta)
        z = random.uniform(-0.9 * pipe_length, 0.9 * pipe_length)
        r = random.uniform(0.1 * pipe_radius, 0.2 * pipe_radius)
        radius = random.uniform(0.1 * pipe_radius, 0.3 * pipe_radius)
        theta = random.uniform(0, 2 * math.pi)
        
        receiver_data = {
            'type': 'Sphere type',
            'name': f"#{receiver_id}-Sphere type",
            'radius': radius,  # radius for the receiver in [0.1..0.3]*pipe radius
            'z': z,
            'r': r,
            'theta': theta
        }
        pipes[pipe_idx]['receivers'].append(receiver_data)
        receiver_id += 1

    # -------------------------------
    # 5) Place a single Emitter
    # -------------------------------
    # choose exactly one pipe to have an emitter
    # Weighted random selection: lower depth = higher chance
    # I might need to change or remove this weigthed selection later because it can create a bias for the ml model
    depths = [pipe.get('depth', 0) for pipe in pipes]
    max_depth = max(depths)
    # Use exponential decay for weights
    alpha = 1.0 / (max_depth + 1) if max_depth > 0 else 1.0
    weights = [math.exp(-alpha * d) for d in depths]
    total_weight = sum(weights)
    norm_weights = [w / total_weight for w in weights]
    emitter_pipe_idx = random.choices(range(pipe_count), weights=norm_weights, k=1)[0]
    emitter_pipe_radius = pipes[emitter_pipe_idx]['radius']
    emitter_pipe_length = pipes[emitter_pipe_idx]['length']
    
    # random emitter position
    z = random.uniform(-0.9 * emitter_pipe_length, 0.9 * emitter_pipe_length)
    r = random.uniform(0.1 * emitter_pipe_radius, 0.9 * emitter_pipe_radius)
    theta = random.uniform(0, 2 * math.pi)
    
    # random single integer for emitter_pattern (converted to string)
    emitter_pattern_int = random.randint(min_particle_count, max_particle_count)
    
    emitter_data = {
        'z': z,
        'r': r,
        'theta': theta,
        'emitter_pattern': str(emitter_pattern_int),
        'emitter_pattern_type': 'complete'
    }
    pipes[emitter_pipe_idx]['emitters'].append(emitter_data)

    # -------------------------------
    # 6) Determine leaf pipes and attach sinks
    # -------------------------------
    # We'll collect all leaf pipes: those that have no children in right_connections.
    # For each leaf pipe, we create a sink.
    sinks = {}
    sink_count = 0

    for pipe in pipes:
        if len(pipe['right_connections']) == 0:
            # This pipe is a leaf, so it will have a sink
            sink_count += 1
            sink_name = f"sink{sink_count}"
            pipe['right_connections'].append(sink_name)
            sinks[sink_name] = {
                'left_connections': [pipe['name']]
            }
            # I will also add a receiver to the end of each leaf node for now.
            receiver_data = {
                'type': 'Sphere type',
                'name': f"#{receiver_id}-Sphere type",
                'radius': pipe['radius'],
                'z': pipe['length'],
                'r': 0,
                'theta': 0
            }
            pipe['receivers'].append(receiver_data)
            receiver_id += 1

    # -------------------------------
    # 7) Build final YAML structure
    # -------------------------------
    # We'll create a dictionary with "pipes" and "sinks" at the top level
    pipes_dict = {}
    for pipe in pipes:
        # Build the data structure for each pipe
        pipe_name = pipe['name']
        
        # For YAML output, we want:
        #   length, radius, particle_count (ignore or set 0?), left_connections, right_connections, flow, emitters, receivers
        # But we do not use 'particle_count' as requested, so we set it to 0 or omit it entirely.
        
        pipe_info = {
            'length': pipe['length'],
            'radius': pipe['radius'],
            'particle_count': 0,  # always 0 or omitted if you'd like
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
    for i in range(n):
        yaml_output = generate_pipe_tree_yaml(
            min_pipe_num=10,
            max_pipe_num=20,
            min_pipe_radius=0.0001,
            max_pipe_radius=0.0005,
            min_pipe_length=0.002,
            max_pipe_length=0.005,
            flow_value=0.01,
            min_particle_count=1000,
            max_particle_count=4000)
    
        # Save to file
        with open(f"configs/network_config_{i}.yaml", "w") as f:
            f.write(yaml_output)
    


if __name__ == "__main__":
    generate_n_times(20)
