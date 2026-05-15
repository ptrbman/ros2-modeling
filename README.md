# ros2-modeling

To run the experiments found in the paper, please see instructions below.

# Prerequisites
You need Python (this was tested with Python 3.10.12)

# Installation of UPPAAL
The UPPAAL model checker needs to be installed (distributed by third party under a separate license): https://uppaal.org/

Download and install according to instructions. Ensure a symbolic link (shortcut) is accesible in the root-directory of ros2-modeling (this project) named "verifyta" to the verifyta-executable of UPPAAL.

The experiments of the paper was run using UPPAAL 5.0.0.

# Running experiments FSEN2025
Enter the root directory and execute command:
```python demo.py```

This will run the the use case of the paper and output .txt-files with latex tables. Total runtime should be less than five minutes on a normal laptop. You can also uncomment lines to run the example and validation case.

# Running experiments ISoLA 2026
Enter the isola folder and then follow the instructions in README.md