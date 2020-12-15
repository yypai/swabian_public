# for TimeTagger
from TimeTagger import setLogger, createTimeTagger, Combiner, Coincidence, Counter, Countrate
from TimeTagger import Correlation, TimeDifferences, TimeTagStream, Scope, Event, CHANNEL_UNUSED
from TimeTagger import UNKNOWN, LOW, HIGH, Histogram
from pylab import *

# for PulseStreamer
from pulsestreamer import PulseStreamer
from pulsestreamer import TriggerStart, TriggerRearm
from pulsestreamer import Sequence, OutputState
import six

#Utilities
from matplotlib import pyplot as plt
import numpy as np
import time
import pandas as pd
from datetime import datetime







# set up time tagger
'''
def log_handler(level, msg):
    if level >= LOGGER_WARNING:
        print(msg)

setLogger(log_handler)
'''

tagger = createTimeTagger()
tagger.reset()

START_CH = 3
CLICK_CH = 2 # the actual signal from APD or SNSPD

tagger.setTriggerLevel(CLICK_CH, 1) # trigger level 0.2
tagger.setTriggerLevel(START_CH, 1) # trigger level 0.2
#tagger.setTestSignal(1, True) # if using internal test pulses
#tagger.setTestSignal(2, True) # if using internal test pulses

# set up pulse streammer
ip_hostname='169.254.8.2'
pulser = PulseStreamer(ip_hostname)
HIGH = 1
LOW = 0

def all_zero(pulser):
    """setting Pulsestreamer constant (LOW)"""
    pulser.constant(OutputState.ZERO())

all_zero(pulser)





import socket
from time import sleep

ip_dict = {"x": '169.254.247.86', "y": '169.254.92.181',  "z": '169.254.96.218'}
PORT = 7180;

magnet_state = [
    '0 Return Value Meaning',
    '1 RAMPING to target field/current',
    '2 HOLDING at the target field/current',
    '3 PAUSED',
    '4 Ramping in MANUAL UP mode',
    '5 Ramping in MANUAL DOWN mode',
    '6 ZEROING CURRENT (in progress)',
    '7 Quench detected',
    '8 At ZERO current',
    '9 Heating persistent switch',
    '10 Cooling persistent switch',
    '11 External Rampdown active',
]

def get_field_unit(handler):
    handler.sendall("FIELD:UNITS?\n".encode())
    reply = handler.recv(2000).decode()
    reply = int(reply.strip())
    return ['kilogauss', 'tesla'][reply]

def get_field(handler):
    handler.sendall("FIELD:Magnet?\n".encode())
    reply = handler.recv(2000).decode()
    return float(reply.strip())

def ramp(handler):
    handler.sendall("RAMP\n".encode())
    print('ramping')

def set_target_field(handler, kilogauss):
    message = "CONFigure:FIELD:TARGet:{kilogauss:.5f}\n"
    message = message.format(kilogauss = kilogauss)
    print(message)
    handler.sendall(message.encode())

def get_state(handler):
    handler.sendall("State?\n".encode())
    reply = magnet_state[int(handler.recv(2000).decode())]
    return reply

def make_triangle(max_field, num_points):
    mat = np.linspace(0, max_field, num_points)
    mat = np.hstack([mat[:-1], mat[::-1]])
    return np.hstack([mat[:-1], -mat])



z = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
z.connect((ip_dict["z"], PORT))
print(z.recv(2000).decode())

BS = make_triangle(60, 7)#1, 141 #Unit is kGause; 1 kG = 0.1 T #141

for j, B in enumerate(BS):

    set_target_field(z, B)
    ramp(z)

    while get_state(z) != '2 HOLDING at the target field/current':
        sleep(0.3)
        print('z', get_state(z),  get_field(z), end = "\r")

    print('z at target: ', get_field(z))
    sleep(1)












    ch_532              = 1 # output channel 0
    ch_apd_start        = 4 # output channel 4
    #ch_apdtime          = 0 # output channel 4

    n_runs = 1e6

    # sweep delta tau
    delta_taus = np.linspace(0, 200000, 5)
    #delta_taus = np.hstack([delta_taus, 0])

    for i, delta_tau in enumerate(delta_taus):

        init_width   =  500000
        readout_width = 500000
        seq_532      =      [(init_width, HIGH), (delta_tau, LOW), (readout_width, HIGH), (300, LOW) ]
        seq_apd_start =     [(init_width, HIGH), (delta_tau + readout_width + 300, LOW) ] # really whatever

        # fake APD signal; don't care
        # seq_apdtime  =      [(10000 - 300, LOW), (300, HIGH), (pulse_period_ns - 10000, LOW) ]
        pulse_period_ns = init_width + delta_tau + readout_width + 300 #2ms

        seq = Sequence()
        seq.setDigital(ch_532,       seq_532)
        seq.setDigital(ch_apd_start, seq_apd_start)
        #seq.setDigital(ch_apdtime,   seq_apdtime)

        pulser.reset()
        pulser.constant(OutputState.ZERO())
        final = OutputState.ZERO()

        start = TriggerStart.IMMEDIATE
        rearm = TriggerRearm.MANUAL

        pulser.setTrigger(start=start, rearm=rearm)
        print ("\nGenerated sequence pulse list:")
        print ("Data format: Sequence as a list of sequence steps (duration [ns], digital bit pattern, analog 0, analog 1)")
        print(seq.getData())
        print("\nThe channel pulse pattern are shown in a Pop-Up window. To proceed with streaming the sequence, please close the sequence plot.")
        #seq.plot()
        print ("\nOutput running on Pulse Streamer")

        tagger.sync()
        binwidth = 10000
        histogram_length = pulse_period_ns * 1e3 * 0.999/binwidth

        hist = Histogram(tagger, CLICK_CH, START_CH, binwidth, int(histogram_length)) # bin width = 20 ns, 10000 bins 200 uS total

        time.sleep(.2) # give time tagger time to start
        pulser.stream(seq, n_runs, final) # start streaming pulses
        #pause(pulse_period_ns * 1e-9 * n_runs) # just set some number such that pulse stream finished by this time; 50 uS * 3000 runs = 0.15 sec.
        for _wait in range(int(n_runs/1000)+2):
            pause(pulse_period_ns * 1e-9 * n_runs/1000)
            print("dt:", delta_tau, "run:", _wait * 1000, end = '\r')
        # n_run = 299792,

        data = hist.getData()
        ind  = hist.getIndex() # in pico seconds

        #plt.plot(ind, data)
        #plt.show()

        print("total counts:", np.sum(np.array(data)), "; length: ", len(data))

        if i == 0:
            data_container = np.vstack([ind, data])
        else:
            print(data.shape[0])
            print(data_container.shape[1])
            print(data.shape[0] - data_container.shape[1])
            data_container = np.hstack([data_container, np.zeros([data_container.shape[0], data.shape[0] - data_container.shape[1]])])

            data_container = np.vstack([data_container, data])
            data_container[0] = ind

    columns = ['time (ps)'] + [str(int(t))+" (ns)" for t in delta_taus]
    df = pd.DataFrame(data_container.T, columns = columns )
    df.to_csv("NV_t1\{:%Y-%m-%d-%H-%M-%S%z}_nruns{:.0f}.csv".format(datetime.now(), n_runs), index = False)
