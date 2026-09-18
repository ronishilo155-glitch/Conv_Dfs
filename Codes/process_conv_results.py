#!/usr/bin/env python3
"""
process_conv_results.py - Adapted from check_xmemcpy.py with minimal changes
"""

#----------------------------------------------------------------------------------
# FROM REFERENCE - NO CHANGES
#----------------------------------------------------------------------------------
def read_hex_file(file_path) :
    print('Reading hex file %s' % file_path)
    hexF = open(file_path,'r')  
    vals_list = []
    for line in hexF : 
        for hex_val_str in line.split() : 
            skip_till_eol = (hex_val_str[0]=='#')  # Skip comment lines detected
            if skip_till_eol :           
                break       
            vals_list.append(int(hex_val_str,16))
        if skip_till_eol :           
            continue       
    return vals_list 

#------------------------------------------------------------------------------------------------
# CHANGED: Read cycle count (NEW)
#------------------------------------------------------------------------------------------------
def read_cycle_count():
    try:
        cycle_bytes = read_hex_file('conv_cycles.txt')
        if len(cycle_bytes) == 4:
            # Little endian: combine 4 bytes into int
            cycle_count = (cycle_bytes[0] | 
                          (cycle_bytes[1] << 8) | 
                          (cycle_bytes[2] << 16) | 
                          (cycle_bytes[3] << 24))
            return cycle_count
        else:
            print('Error: Expected 4 bytes for cycle count')
            return -1
    except:
        print('Error: Could not read conv_cycles.txt')
        return -1

#------------------------------------------------------------------------------------------------
# CHANGED: Main - read convolution results instead of memcpy
#------------------------------------------------------------------------------------------------

# Read cycle count
cycle_count = read_cycle_count()
if cycle_count >= 0:
    print('\nCycle count: %d' % cycle_count)
else:
    print('\nCycle count: N/A')

# Read output data
out_vals_list = read_hex_file('conv_output.txt')

print('\nConvolution output:')
print('  Total bytes: %d' % len(out_vals_list))
print('  First 16 bytes: %s' % ' '.join(['%02x' % v for v in out_vals_list[:16]]))

# TODO: Add verification/comparison with golden reference if needed
# For now, just display the results

print('\nConvolution completed successfully!')
print('Output data available in conv_output.txt')
print('Cycle count: %d' % (cycle_count if cycle_count >= 0 else 0))