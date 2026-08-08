#!/usr/bin/env bash

set -e # Stop script execution if any run.sh fails

# List of directories to process
directories=(
    "BioMistral"
    "BioMistralFinetuned"
    "medgemma"
)

echo "Starting sequential execution of run.sh scripts..."
echo "================================================="

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        if [ -f "$dir/run.sh" ]; then
            echo ""
            echo "-------------------------------------------------"
            echo "Entering directory: $dir"
            echo "-------------------------------------------------"
            
            # Enter directory, run script, and return to original root directory
            (
                cd "$dir" || exit 1
                chmod +x run.sh
                ./run.sh
            )
            
            echo "Finished execution for $dir"
        else
            echo "Warning: No run.sh found in $dir. Skipping."
        fi
    else
        echo "Warning: Directory $dir does not exist. Skipping."
    fi
done

echo ""
echo "================================================="
echo "All scripts executed successfully!"
