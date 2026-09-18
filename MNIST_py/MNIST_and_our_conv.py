import numpy as np
import h5py
import copy
import ctypes
import os
from random import randint

# ============================================================
# CONFIGURATION
# ============================================================

# Toggle between Python convolution and C convolution
USE_OUR_CONV = True   # False = pure Python baseline, True = use C convolution

# Path to compiled C library
# Update if needed
C_LIB_PATH = r"C:\Users\97252\PycharmProjects\pythonProject4\pipeline.dll"       # Windows
# C_LIB_PATH = "./libconv_pipeline.so"    # Linux

print("cwd:", os.getcwd())
print("dll exists:", os.path.exists(C_LIB_PATH))


if USE_OUR_CONV:
    c_lib = ctypes.CDLL(C_LIB_PATH)

    c_lib.run_c_pipeline_bridge.argtypes = [
        ctypes.POINTER(ctypes.c_float),  # input_flat
        ctypes.c_int,                    # N
        ctypes.POINTER(ctypes.c_float),  # kernel_flat (2x2)
        ctypes.POINTER(ctypes.c_float),  # output_flat
        ctypes.POINTER(ctypes.c_int)     # out_dim_result
    ]

# ============================================================
# LOAD MNIST DATA
# ============================================================

MNIST_data = h5py.File('MNISTdata.hdf5', 'r')
x_train = np.float32(MNIST_data['x_train'][:])
y_train = np.int32(np.array(MNIST_data['y_train'][:, 0]))
x_test = np.float32(MNIST_data['x_test'][:])
y_test = np.int32(np.array(MNIST_data['y_test'][:, 0]))
MNIST_data.close()

# ============================================================
# HELPER FUNCTIONS FOR C CONVOLUTION
# ============================================================

def pad_28_to_32(img_28):
    padded = np.zeros((32, 32), dtype=np.float32)
    # Symmetric padding: center the 28x28 image within the 32x32 frame
    padded[2:30, 2:30] = img_28
    return padded
def expand_to_26x26(small):
    h, w = small.shape
    out = np.zeros((26, 26), dtype=np.float32)

    # Calculate offset to center the 16x16 image in the 26x26 grid
    # (26 - 16) / 2 = 5
    offset_h = (26 - h) // 2
    offset_w = (26 - w) // 2

    for i in range(h):
        for j in range(w):
            # Place each pixel from the small image into the centered position
            out[i + offset_h, j + offset_w] = small[i, j]

    return out

# ============================================================
# CNN CLASS
# ============================================================

class CNN:
    kernals = {}
    output_layer = {}
    hppr = {}

    def __init__(self, num_iterations, l_rate, stride, padding,
                 dim_kernal, num_kernals, dim_inputs, len_outputs,
                 input_chanl, batch_size=1):

        self.hppr = {
            "batch_size": batch_size,
            "num_iterations": num_iterations,
            "l_rate": l_rate,
            "stride": stride,
            "padding": padding,
            "dim_kernal": dim_kernal,
            "num_kernals": num_kernals,
            "dim_inputs": dim_inputs,
            "len_outputs": len_outputs,
            "input_chanl": input_chanl
        }

        # Fix: Override temp_dim to 26 when using our conv (to match the 26x26 output)
        if USE_OUR_CONV:
            temp_dim = 26
        else:
            temp_dim = dim_inputs - dim_kernal + 1

        self.output_layer = {
            'para': np.random.randn(len_outputs, num_kernals, temp_dim, temp_dim)
                    / np.sqrt(temp_dim ** 2 * num_kernals),
            'bias': np.zeros((len_outputs, 1))
        }

        self.kernals = {}
        for i in range(num_kernals):
            self.kernals[i] = np.random.randn(input_chanl, dim_kernal, dim_kernal) \
                              / np.sqrt(dim_kernal ** 2)

    # ------------------------------------------------------------
    # Print model parameters
    # ------------------------------------------------------------
    def printing(self):
        print('########## Hyperparameters ##########')
        for i, j in self.kernals.items():
            print('kernel', i, ':', j.shape)
        for i, j in self.output_layer.items():
            print(i, ':', j.shape)
        for i, j in self.hppr.items():
            print(i, ':', j)
        print('#####################################')

    # ------------------------------------------------------------
    # Activation function
    # ------------------------------------------------------------
    def activfunc(self, Z, type='ReLU', deri=False):
        if type == 'ReLU':
            if deri:
                return (Z > 0).astype(np.float32)
            return Z * (Z > 0)

    # ------------------------------------------------------------
    # Stable Softmax
    # ------------------------------------------------------------
    def Softmax(self, z):
        z = z - np.max(z)
        exp_z = np.exp(z)
        return exp_z / np.sum(exp_z)

    # ------------------------------------------------------------
    # Cross entropy loss
    # ------------------------------------------------------------
    def cross_entropy_error(self, p, y):
        eps = 1e-9
        return -np.log(p[y] + eps)

    # ------------------------------------------------------------
    # Convolution layer (Python or C)
    # ------------------------------------------------------------
    def convolution(self, x, kernals):

        if not USE_OUR_CONV:
            # ---------- Python convolution (Original Logic) ----------
            num_kernals = len(kernals)
            x_sp = x.shape
            k_sp = kernals[0].shape
            t_dim = x_sp[1] - k_sp[1] + 1

            result = np.zeros((num_kernals, t_dim, t_dim))
            for i in range(num_kernals):
                for j in range(t_dim):
                    for k in range(t_dim):
                        result[i, j, k] = np.sum(
                            kernals[i] * x[:, j:j + k_sp[1], k:k + k_sp[2]]
                        )
            return result

        else:
            # ---------- C convolution logic ----------

            # FIX: Check if this is a Backpropagation call (Gradient calculation)
            # If the kernel size is large (>2), it means we are calculating gradients (dK).
            # The C accelerator cannot do this, so we must do the math here locally.
            if kernals[0].shape[1] > 2:
                num_kernals = len(kernals)
                x_sp = x.shape
                k_sp = kernals[0].shape
                t_dim = x_sp[1] - k_sp[1] + 1

                result = np.zeros((num_kernals, t_dim, t_dim))
                for i in range(num_kernals):
                    for j in range(t_dim):
                        for k in range(t_dim):
                            result[i, j, k] = np.sum(
                                kernals[i] * x[:, j:j + k_sp[1], k:k + k_sp[2]]
                            )
                # Crop to 2x2 to match our kernel size
                return result[:, :2, :2]

            # ---------- Forward Pass (Using C Accelerator) ----------
            # If we are here, it's a standard forward pass with 2x2 kernels.

            # 1. Symmetric Pad input
            img_28 = x[0]
            img_32 = pad_28_to_32(img_28)
            input_flat = img_32.flatten().astype(np.float32)

            num_kernals = len(kernals)
            result = np.zeros((num_kernals, 26, 26), dtype=np.float32)

            # 2. Loop over kernels
            for i in range(num_kernals):
                k = kernals[i][0]
                kernel_2x2 = k.flatten().astype(np.float32)

                output_flat = np.zeros(32 * 32, dtype=np.float32)
                out_dim = ctypes.c_int()

                # 3. Call C convolution directly
                c_lib.run_c_pipeline_bridge(
                    input_flat.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    ctypes.c_int(32),
                    kernel_2x2.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    output_flat.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    ctypes.byref(out_dim)
                )

                # 4. Extract and Expand
                out_dim_val = out_dim.value
                out_small = output_flat[:out_dim_val * out_dim_val]
                out_small = out_small.reshape((out_dim_val, out_dim_val))

                result[i] = expand_to_26x26(out_small)

            return result

    # ------------------------------------------------------------
    # Forward pass
    # ------------------------------------------------------------
    def forward(self, x, y):
        dim = self.hppr['dim_inputs']
        X = x.reshape(self.hppr['input_chanl'], dim, dim)

        Z = self.convolution(X, self.kernals)
        H = self.activfunc(Z).reshape((-1, 1))

        W = self.output_layer['para'].reshape((10, -1))
        U = np.matmul(W, H) + self.output_layer['bias']

        predict_list = np.squeeze(self.Softmax(U))
        error = self.cross_entropy_error(predict_list, y)

        return {
            'Z': Z,
            'H': H,
            'U': U,
            'f_X': predict_list.reshape((1, self.hppr['len_outputs'])),
            'error': error
        }

    # ------------------------------------------------------------
    # Backpropagation
    # ------------------------------------------------------------
    def back_propagation(self, x, y, f_result):
        E = np.zeros((1, self.hppr['len_outputs']))
        E[0][y] = 1

        dU = (f_result['f_X'] - E).reshape((self.hppr['len_outputs'], 1))
        db = dU

        delta = np.zeros((self.hppr['num_kernals'], 26, 26))
        for i in range(10):
            delta += self.output_layer['para'][i] * dU[i]

        dW = np.zeros((10, 5, 26, 26))
        for i in range(10):
            dW[i] = dU[i] * f_result['H'].reshape((5, 26, 26))

        dK = {}
        for i in range(5):
            tmp = {0: delta[i:i+1]}
            dK[i] = self.convolution(x.reshape((1, 28, 28)), tmp)

        return {'db': db, 'dW': dW, 'dK': dK}

    # ------------------------------------------------------------
    # Parameter update
    # ------------------------------------------------------------
    def optimize(self, b_result, learning_rate):
        self.output_layer['para'] -= learning_rate * b_result['dW']
        self.output_layer['bias'] -= learning_rate * b_result['db']

        # TIKUN: We removed the "if not USE_OUR_CONV" check here.
        # We MUST update kernels even when using C code, otherwise the network won't learn!
        for i in range(5):
            self.kernals[i] -= learning_rate * b_result['dK'][i]

    # ------------------------------------------------------------
    # Training loop (original prints)
    # ------------------------------------------------------------
    def train(self, X_train, Y_train):
        learning_rate = self.hppr['l_rate']
        num_iterations = self.hppr['num_iterations']
        rand_indices = np.random.choice(len(X_train), num_iterations, replace=True)

        count = 1
        loss_dict = {}
        test_dict = {}

        for i in rand_indices:
            f_result = self.forward(X_train[i], Y_train[i])
            b_result = self.back_propagation(X_train[i], Y_train[i], f_result)
            self.optimize(b_result, learning_rate)

            if count % 100 == 0:
                if count % 30000 == 0:
                    loss = 'NA'
                    test = self.testing(x_test, y_test)
                    print('Trained for {} times,'.format(count),
                          'loss = {}, test = {}'.format(loss, test))
                    test_dict[str(count)] = test
                else:
                    print('Trained for {} times,'.format(count))
            count += 1

        print('Training finished!')
        return loss_dict, test_dict

    # ------------------------------------------------------------
    # Testing
    # ------------------------------------------------------------
    def testing(self, X_test, Y_test):
        total_correct = 0
        for n in range(len(X_test)):
            y = Y_test[n]
            x = X_test[n][:]
            prediction = np.argmax(self.forward(x, y)['f_X'])
            if prediction == y:
                total_correct += 1
            if n % 1000 == 0:
                print('testing data', n)
        print('Accuarcy Test: ', total_correct / len(X_test))
        return total_correct / float(len(X_test))

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    # Set parameters based on the flag:
    # If using C code -> Kernel 2x2, Stride 2.
    if USE_OUR_CONV:
        current_dim_kernal = 2
        current_stride = 2
    else:
        current_dim_kernal = 3
        current_stride = 1

    model = CNN(
    batch_size=1,
    num_iterations=120000,
    l_rate=0.001,
    stride=current_stride,         # Updated based on flag
    padding=0,
    dim_kernal=current_dim_kernal, # Updated based on flag
    num_kernals=5,
    dim_inputs=28,
    input_chanl=1,
    len_outputs=10
    )

    # Execution lines remain exactly the same
    model.printing()
    cost_dict, tests_dict = model.train(x_train, y_train)
    accu = model.testing(x_test, y_test)
    model.printing()
