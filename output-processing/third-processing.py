import os
import glob
import numpy as np
import torch
import random

# Constants from the user's configuration
MAX_PIPES = 100
MAX_RECEIVERS = 200
PIPE_OH_DIM = MAX_PIPES          # one‑hot length
PIPE_FEAT_DIM = PIPE_OH_DIM*2 + 3  # (self OH) + (parent OH) + length,radius,numRecv
RECV_FEAT_DIM = PIPE_OH_DIM + 10   # (pipe OH) + r,z,rad + 7 stats
GLOBAL_DIM = 2                  # diffusion, flow
INPUT_DIM = GLOBAL_DIM + MAX_PIPES*PIPE_FEAT_DIM + MAX_RECEIVERS*RECV_FEAT_DIM
TARGET_DIM = PIPE_OH_DIM + 2                  # pipe_id (one-hot), r, z

def one_hot(index: int, length: int=MAX_PIPES):
    vec = np.zeros(length, dtype=np.float32)
    if 0 <= index < length:
        vec[index] = 1.0
    return vec

def process_sample(sim_dir):
    """Process a single sample directory and return feature vector and target."""
    # -------- global ------------------------------------------------
    diffusion, flow = np.loadtxt(os.path.join(sim_dir, "meta.txt"), dtype=np.float32)

    # -------- pipes -------------------------------------------------
    pipes_raw = np.loadtxt(os.path.join(sim_dir, "pipes.txt"), dtype=np.float32, ndmin=2)
    pipe_mat = np.zeros((MAX_PIPES, PIPE_FEAT_DIM), dtype=np.float32)

    for row in pipes_raw[:MAX_PIPES]:
        p_id, parent_id, length, radius, nrecv = row
        p_id, parent_id, nrecv = map(int, (p_id, parent_id, nrecv))
        vec = np.concatenate([
            one_hot(p_id),                # self ID
            one_hot(parent_id)            # parent ID  (parent_id==-1 gives zeros)
            if parent_id >= 0 else np.zeros(PIPE_OH_DIM, np.float32),
            np.array([length, radius, nrecv], np.float32)
        ])
        pipe_mat[p_id] = vec

    # -------- receivers --------------------------------------------
    recv_mat = np.zeros((MAX_RECEIVERS, RECV_FEAT_DIM), dtype=np.float32)
    rec_path = os.path.join(sim_dir, "receivers.txt")
    if os.path.exists(rec_path) and os.path.getsize(rec_path) > 0:  # receivers.txt might be empty
        recv_raw = np.loadtxt(rec_path, dtype=np.float32, ndmin=2)
        for i, row in enumerate(recv_raw[:MAX_RECEIVERS]):
            (p_id, r, z, rad,
             first_t, max_val, max_t,
             total, mean, std, skew) = row
            p_id = int(p_id)
            vec = np.concatenate([
                one_hot(p_id),                        # pipe identity
                np.array([r, z, rad,
                          first_t, max_val, max_t,
                          total, mean, std, skew], np.float32)
            ])
            recv_mat[i] = vec

    # -------- target -----------------------------------------------
    t_pipe, t_r, t_z = np.loadtxt(os.path.join(sim_dir, "target.txt"), dtype=np.float32)
    pipe_one_hot = one_hot(int(t_pipe))  # Convert pipe ID to one-hot encoding
    target = np.concatenate([
        pipe_one_hot,
        np.array([t_r, t_z], np.float32)
    ])

    # -------- stack -------------------------------------------------
    x = np.concatenate([
        np.array([diffusion, flow], np.float32),
        pipe_mat.flatten(),
        recv_mat.flatten()
    ])
    
    return x, target

def convert_to_npz(source_dir, output_file):
    """
    Convert all samples in source_dir to a single npz file.
    
    Args:
        source_dir: Directory containing the processed samples
        output_file: Path to the output .npz file
    """
    # Get all sample directories
    sample_dirs = sorted(glob.glob(os.path.join(source_dir, "*")))
    
    if not sample_dirs:
        print(f"No samples found in {source_dir}")
        return
    
    # Process all samples
    features = []
    targets = []
    
    for sim_dir in sample_dirs:
        try:
            x, y = process_sample(sim_dir)
            features.append(x)
            targets.append(y)
        except Exception as e:
            print(f"Error processing {sim_dir}: {e}")
    
    # Convert to numpy arrays
    features = np.array(features, dtype=np.float32)
    targets = np.array(targets, dtype=np.float32)
    
    # Save to npz file
    np.savez(output_file, x=features, y=targets)
    
    print(f"Saved {len(features)} samples to {output_file}")
    print(f"Features shape: {features.shape}, Targets shape: {targets.shape}")

if __name__ == "__main__":
    # Paths to the processed data directories
    train_dir = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/train-data"
    validation_dir = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/validation-data"
    
    # Output npz files
    train_npz = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/train.npz"
    validation_npz = "/Users/daghanerdonmez/Desktop/molecular-simulation-mlp/output-processing/validation.npz"
    
    # Convert training data
    print("Processing training data...")
    convert_to_npz(train_dir, train_npz)
    
    # Convert validation data
    print("Processing validation data...")
    convert_to_npz(validation_dir, validation_npz)
    
    print("Processing complete.")
