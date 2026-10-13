from base64 import b64encode, b64decode
import hashlib
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from PIL import Image

from qiskit import *
from qiskit_aer import Aer
from qiskit.providers.basic_provider import BasicProvider
import math
import numpy as np
import random
import re
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

qr = QuantumRegister(2, name="qr")
cr = ClassicalRegister(4, name="cr")
singlet = QuantumCircuit(qr, cr, name='singlet')
singlet.h(qr[0])
singlet.cx(qr[0],qr[1])

measureA1 = QuantumCircuit(qr, cr, name='measureA1')
measureA1.h(qr[0])
measureA1.measure(qr[0],cr[0])

measureA2 = QuantumCircuit(qr, cr, name='measureA2')
measureA2.s(qr[0])
measureA2.h(qr[0])
measureA2.t(qr[0])
measureA2.h(qr[0])
measureA2.measure(qr[0],cr[0])

measureA3 = QuantumCircuit(qr, cr, name='measureA3')
measureA3.measure(qr[0],cr[0])

## Bob's measurement circuits

# measure the spin projection of Bob's qubit onto the b_1 direction (W basis)
measureB1 = QuantumCircuit(qr, cr, name='measureB1')
measureB1.s(qr[1])
measureB1.h(qr[1])
measureB1.t(qr[1])
measureB1.h(qr[1])
measureB1.measure(qr[1],cr[1])

# measure the spin projection of Bob's qubit onto the b_2 direction (standard Z basis)
measureB2 = QuantumCircuit(qr, cr, name='measureB2')
measureB2.measure(qr[1],cr[1])

# measure the spin projection of Bob's qubit onto the b_3 direction (V basis)
measureB3 = QuantumCircuit(qr, cr, name='measureB3')
measureB3.s(qr[1])
measureB3.h(qr[1])
measureB3.tdg(qr[1])
measureB3.h(qr[1])
measureB3.measure(qr[1],cr[1])

## Lists of measurement circuits
aliceMeasurements = [measureA1, measureA2, measureA3]
bobMeasurements = [measureB1, measureB2, measureB3]
numberOfSinglets = 500
aliceMeasurementChoices = [random.randint(1, 3) for i in range(numberOfSinglets)] # string b of Alice
bobMeasurementChoices = [random.randint(1, 3) for i in range(numberOfSinglets)] # string b' of Bob
circuits = [] # the list in which the created circuits will be stored

for i in range(numberOfSinglets):
    circuitName = singlet & aliceMeasurements[aliceMeasurementChoices[i]-1] & bobMeasurements[bobMeasurementChoices[i]-1]
    circuits.append(circuitName)

## Record Results
results = []
for i in range (numberOfSinglets):
  simulator = Aer.get_backend("qasm_simulator")
  backend = BasicProvider().get_backend('basic_simulator')
  transpiled_circuit = transpile(circuits[i], backend)

  result = backend.run(transpiled_circuit, shots = 1).result()
  results.append(result)
results[499].get_counts().keys()
abPatterns = [
    re.compile('..00$'), # search for the '..00' output (Alice obtained 0 and Bob obtained 0)
    re.compile('..01$'), # search for the '..01' output
    re.compile('..10$'), # search for the '..10' output (Alice obtained 0 and Bob obtained 1)
    re.compile('..11$')  # search for the '..11' output
]
aliceResults = [] # Alice's results (string a)
bobResults = [] # Bob's results (string a')

for i in range(numberOfSinglets):

    #res = list(result.get_counts(circuits[i]).keys())[0] # extract the key from the dict and transform it to str; execution result of the i-th circuit
    res = str(list(results[i].get_counts().keys())[0])
    if abPatterns[0].search(res): # check if the key is '..00' (if the measurement results are -1,-1)
        aliceResults.append(0) # Alice got the result -1
        bobResults.append(0) # Bob got the result -1
    if abPatterns[1].search(res):
        aliceResults.append(1)
        bobResults.append(0)
    if abPatterns[2].search(res): # check if the key is '..10' (if the measurement results are -1,1)
        aliceResults.append(0) # Alice got the result -1
        bobResults.append(1) # Bob got the result 1
    if abPatterns[3].search(res):
        aliceResults.append(1)
        bobResults.append(1)

## Revealing Base
aliceKey = [] # Alice's key string k
bobKey = [] # Bob's key string k'

# comparing the stings with measurement choices
for i in range(numberOfSinglets):
    # if Alice and Bob have measured the spin projections onto the a_2/b_1 or a_3/b_2 directions
    if (aliceMeasurementChoices[i] == 2 and bobMeasurementChoices[i] == 1) or (aliceMeasurementChoices[i] == 3 and bobMeasurementChoices[i] == 2):
        aliceKey.append(aliceResults[i]) # record the i-th result obtained by Alice as the bit of the secret key k
        bobKey.append(bobResults[i])

keyLength = len(aliceKey) # length of the secret key

abKeyMismatches = 0 # number of mismatching bits in Alice's and Bob's keys

for j in range(keyLength):
    if aliceKey[j] != bobKey[j]:
        abKeyMismatches += 1

aliceKey = ''.join([str(i) for i in aliceKey])
bobKey = ''.join([str(i) for i in bobKey])
print(aliceKey)
print(bobKey)


def encrypt(image_path, key):

    # Load the image and convert it into bytes
    with open(image_path, 'rb') as f:
        image_data = f.read()

    # Encode the image data as a base64 string
    image_data = b64encode(image_data)

    # Create a SHA-256 hash of the key
    key = hashlib.sha256(key.encode()).digest()

    hash_key_key = key.hex()
    print(hash_key_key)

    # Generate a random initialization vector
    iv = get_random_bytes(AES.block_size)

    # Create an AES Cipher object
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # Encrypt the image data
    encrypted_image_data = cipher.encrypt(pad(image_data, AES.block_size))

    # Save the encrypted image data to a new file
    with open(image_path, 'wb') as f:
        f.write(iv + encrypted_image_data)


def decrypt(encrypted_image_path, key):
    # Load the encrypted image data
    with open(encrypted_image_path, 'rb') as f:
        encrypted_image_data = f.read()

    # Create a SHA-256 hash of the key
    key = hashlib.sha256(key.encode()).digest()

    hash_key_key = key.hex()
    print(hash_key_key)

    # Extract the initialization vector from the encrypted image data
    iv = encrypted_image_data[:AES.block_size]
    encrypted_image_data = encrypted_image_data[AES.block_size:]

    # Create an AES Cipher object
    cipher = AES.new(key, AES.MODE_CBC, iv)

    try:
        # Decrypt the encrypted image data
        decrypted_image_data = unpad(cipher.decrypt(encrypted_image_data), AES.block_size)

        # Decode the decrypted image data from a base64 string
        decrypted_image_data = b64decode(decrypted_image_data)

        # Save the decrypted data next to the input, keeping its extension (x.png -> x.dec.png, x.avi -> x.dec.avi)
        path = Path(encrypted_image_path)
        filename = str(path.with_name(path.stem + '.dec' + (path.suffix or '.png')))
        with open(filename, 'wb') as f:
            f.write(decrypted_image_data)

    except ValueError:
        print("Wrong Key ):")
        return -1, None
    return 0, filename
