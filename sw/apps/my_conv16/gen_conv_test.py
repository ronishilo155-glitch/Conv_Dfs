#!/usr/bin/env python3
"""
gen_conv_test.py - Adapted from gen_xmemcpy_test.py with minimal changes
"""

import numpy as np
import random

#--------------------------------------------------------------------------------------
# Little endian and hex print assistance functions (FROM REFERENCE - NO CHANGES)
#--------------------------------------------------------------------------------------

# signed int
def int32_ltlend_hex_str(val):
    val = (val + (1 << 32)) % (1 << 32)
    bigend_hex_str = '%08x' % val
    ltlend_hex_str = '%s %s %s %s ' % (bigend_hex_str[6:8],bigend_hex_str[4:6],bigend_hex_str[2:4],bigend_hex_str[0:2])
    return ltlend_hex_str 

# unsigned int
def uint32_ltlend_hex_str(val):
    bigend_hex_str = '%08x' % val
    ltlend_hex_str = '%s %s %s %s ' % (bigend_hex_str[6:8],bigend_hex_str[4:6],bigend_hex_str[2:4],bigend_hex_str[0:2])
    return ltlend_hex_str 

# signed char
def int8_hex_str(val): 
    val = (val + (1 << 8)) % (1 << 8)
    return '%02x' % val

#-------------------------------------------------------------------------------------
# Xbox hard configuration (FROM REFERENCE - NO CHANGES)
#-------------------------------------------------------------------------------------
XBOX_TCM_BASE_ADDR = 0x40000000
XMEM_SIZE = 2*1024*32  # size in bytes 

#-------------------------------------------------------------------------------------
# CHANGED: Configuration for convolution instead of memcpy
#-------------------------------------------------------------------------------------

# Input size (choose: 16, 32, 64, 128, 256)
N = 256

# Kernel size
KERNEL_SIZE = 2

# Other params
STRIDE = 2
PADDING = 0

# Calculate sizes
input_num_bytes = N * N  # treating as bytes (can be float later)
kernel_num_bytes = KERNEL_SIZE * KERNEL_SIZE
output_dim = 16  # Based on your pipeline depth
output_num_bytes = output_dim * output_dim

# Memory addresses (similar to reference)
# Memory addresses (Updated to fit inside 64KB XMEM)
input_addr = XBOX_TCM_BASE_ADDR + 0x0000   # Offset 0
kernel_addr = XBOX_TCM_BASE_ADDR + 0x4000  # Offset 16KB 
output_addr = XBOX_TCM_BASE_ADDR + 0x8000  # Offset 32KB 

#-------------------------------------------------------------------------------------
# CHANGED: Write convolution configuration file
#-------------------------------------------------------------------------------------
config_file = open('conv_config.txt','w')
config_file.write('# Notice ALL values are in hex bytes\n')
config_file.write('# Notice int words are provided in little endian (value least significant byte is first)\n\n')

config_file.write('%s # input_addr = %08x \n' % (uint32_ltlend_hex_str(input_addr), input_addr))
config_file.write('%s # kernel_addr = %08x \n' % (uint32_ltlend_hex_str(kernel_addr), kernel_addr))
config_file.write('%s # output_addr = %08x \n' % (uint32_ltlend_hex_str(output_addr), output_addr))

config_file.write('%s # input_num_bytes = %08x (%d decimal)\n' %  (uint32_ltlend_hex_str(input_num_bytes), input_num_bytes, input_num_bytes))
config_file.write('%s # kernel_num_bytes = %08x (%d decimal)\n' %  (uint32_ltlend_hex_str(kernel_num_bytes), kernel_num_bytes, kernel_num_bytes))
config_file.write('%s # output_num_bytes = %08x (%d decimal)\n' %  (uint32_ltlend_hex_str(output_num_bytes), output_num_bytes, output_num_bytes))

config_file.write('%s # input_height = %08x (%d decimal)\n' %  (int32_ltlend_hex_str(N), N, N))
config_file.write('%s # input_width = %08x (%d decimal)\n' %  (int32_ltlend_hex_str(N), N, N))
config_file.write('%s # kernel_size = %08x (%d decimal)\n' %  (int32_ltlend_hex_str(KERNEL_SIZE), KERNEL_SIZE, KERNEL_SIZE))
config_file.write('%s # stride = %08x (%d decimal)\n' %  (int32_ltlend_hex_str(STRIDE), STRIDE, STRIDE))
config_file.write('%s # padding = %08x (%d decimal)\n' %  (int32_ltlend_hex_str(PADDING), PADDING, PADDING))

config_file.close()

print('Generated conv_config.txt')

#-------------------------------------------------------------------------------------
# CHANGED: Generate random input data (same format as reference)
#-------------------------------------------------------------------------------------
#test_input_vec = np.random.randint(0,256, size=(input_num_bytes))
#test_input_vec = np.ones(input_num_bytes, dtype=np.uint8)
test_input_vec = np.full(input_num_bytes, 200)

#test_input_vec = np.random.randint(0,255, size=(input_num_bytes)) 

test_in_file = open('conv_input.txt','w')
#test_in_file.write('# Convolution input Data (unsigned hex bytes):\n\n')

num_bytes_per_input_line = 32
for i in range(input_num_bytes) : 
    test_in_file.write('%02x' % test_input_vec[i])
    i+=1
    if i%N==0 :
        test_in_file.write('\n')
    else :
        test_in_file.write(' ')

test_in_file.write('\n')
test_in_file.close()

print('Generated conv_input.txt')

#-------------------------------------------------------------------------------------
# NEW: Generate SINGLE kernel (fixed from paper: [[1, 0], [0, 1]])
#-------------------------------------------------------------------------------------
# Single 2x2 kernel
kernel_vec = np.array([1, 1, 1, 1], dtype=np.uint8)  # Identity kernel from paper

test_kernel_file = open('conv_kernels.txt','w')
test_kernel_file.write('# Single Kernel Data (2x2, unsigned hex bytes):\n')
test_kernel_file.write('# Kernel from paper: [[1, 0], [0, 1]]\n\n')

for i in range(kernel_num_bytes) : 
    test_kernel_file.write('%02x' % kernel_vec[i])
    i+=1
    if i%32==0 :
        test_kernel_file.write('\n')
    else :
        test_kernel_file.write(' ')

test_kernel_file.write('\n')
test_kernel_file.close()

print('Generated conv_kernels.txt (single kernel from paper)')

print('\nAll test files generated successfully!')