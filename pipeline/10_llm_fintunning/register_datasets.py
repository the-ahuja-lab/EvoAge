#!/usr/bin/env python3
import os
import sys
import shutil
import json
import argparse
import glob

def parse_args():
    parser = argparse.ArgumentParser(description="Register GraphGen datasets into LLaMA-Factory")
    parser.add_argument("--output_dir", required=True, help="GraphGen run output directory (e.g. cache/output/1234567)")
    parser.add_argument("--llama_dir", default="LLaMA-Factory", help="LLaMA-Factory root directory")
    parser.add_argument("--yaml_file", default="biomistral_lora_sft_optimized4.yaml", help="LLaMA-Factory config YAML file to update")
    return parser.parse_args()

def main():
    args = parse_args()
    
    output_dir = args.output_dir
    llama_dir = args.llama_dir
    yaml_file = args.yaml_file
    
    if not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist.")
        sys.exit(1)
        
    llama_data_dir = os.path.join(llama_dir, "data")
    if not os.path.exists(llama_data_dir):
        print(f"Error: LLaMA-Factory data directory '{llama_data_dir}' not found.")
        sys.exit(1)
        
    dataset_info_path = os.path.join(llama_data_dir, "dataset_info.json")
    if not os.path.exists(dataset_info_path):
        print(f"Warning: '{dataset_info_path}' not found, creating a new one.")
        dataset_info = {}
    else:
        with open(dataset_info_path, "r", encoding="utf-8") as f:
            try:
                dataset_info = json.load(f)
            except Exception as e:
                print(f"Error reading {dataset_info_path}: {e}")
                sys.exit(1)

    # Categories to scan for
    categories = {
        "generate_atomic": "biomedical_atomic",
        "generate_aggregated": "biomedical_aggregated",
        "generate_multi_hop": "biomedical_multi_hop",
        "generate_true_false": "biomedical_true_false"
    }
    
    registered_datasets = []
    
    # We clean old matching keys from dataset_info to avoid cluttering or outdated references
    for val in categories.values():
        keys_to_del = [k for k in dataset_info.keys() if k.startswith(val)]
        for k in keys_to_del:
            del dataset_info[k]

    for cat_dir, prefix in categories.items():
        search_path = os.path.join(output_dir, cat_dir, "*.jsonl")
        jsonl_files = glob.glob(search_path)
        
        if not jsonl_files:
            # Check recursively or directly in output_dir
            search_path_direct = os.path.join(output_dir, "*.jsonl")
            # In some cases GraphGen output format is flat, let's be flexible
            jsonl_files = [f for f in glob.glob(search_path_direct) if cat_dir in os.path.basename(f)]
            
        print(f"Found {len(jsonl_files)} files for category {cat_dir}")
        
        for idx, file_path in enumerate(sorted(jsonl_files)):
            basename = os.path.basename(file_path)
            dest_path = os.path.join(llama_data_dir, basename)
            
            # Copy to LLaMA-Factory data directory
            print(f"Copying {basename} to {llama_data_dir}...")
            shutil.copy2(file_path, dest_path)
            
            # Define dataset key
            dataset_key = f"{prefix}_{idx}"
            
            # Add to dataset_info.json
            dataset_info[dataset_key] = {
                "file_name": basename,
                "formatting": "sharegpt",
                "columns": {
                    "messages": "messages"
                },
                "tags": {
                    "role_tag": "role",
                    "content_tag": "content",
                    "user_tag": "user",
                    "assistant_tag": "assistant",
                    "system_tag": "system"
                }
            }
            registered_datasets.append(dataset_key)

    # Write updated dataset_info.json
    print(f"Updating {dataset_info_path}...")
    with open(dataset_info_path, "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=2, ensure_ascii=False)
        
    # Also update the local dataset_info.json in the current working directory if it exists
    if os.path.exists("dataset_info.json"):
        print("Updating local dataset_info.json in current directory...")
        with open("dataset_info.json", "w", encoding="utf-8") as f:
            json.dump(dataset_info, f, indent=2, ensure_ascii=False)

    # Update YAML file
    if os.path.exists(yaml_file):
        print(f"Updating dataset list in configuration file '{yaml_file}'...")
        with open(yaml_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        dataset_list_str = ", ".join(registered_datasets)
        new_lines = []
        updated = False
        
        for line in lines:
            if line.strip().startswith("dataset:"):
                new_lines.append(f"dataset: {dataset_list_str}\n")
                updated = True
                print(f"Updated dataset line in {yaml_file}")
            else:
                new_lines.append(line)
                
        if not updated:
            # Find the ### dataset line or just append
            new_lines.append(f"\ndataset: {dataset_list_str}\n")
            print(f"Appended dataset line to {yaml_file}")
            
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    else:
        print(f"Warning: Configuration YAML '{yaml_file}' not found. Skipping YAML update.")
        
    print(f"Dataset registration complete. Registered {len(registered_datasets)} datasets:")
    print(", ".join(registered_datasets))

if __name__ == "__main__":
    main()
