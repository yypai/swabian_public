# for TimeTagger
from TimeTagger import setLogger, createTimeTagger, Combiner, Coincidence, Counter, Countrate, Correlation, TimeDifferences, TimeTagStream, Scope, Event, CHANNEL_UNUSED, UNKNOWN, LOW, HIGH, LOGGER_WARNING, Histogram
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

# set up time tagger
def log_handler(level, msg):
    if level >= LOGGER_WARNING:
        print(msg)

setLogger(log_handler)


tagger = createTimeTagger()
tagger.reset()

START_CH = 1
CLICK_CH = 2

tagger.setTriggerLevel(CLICK_CH, 0.2) # trigger level 0.2
tagger.setTriggerLevel(START_CH, 0.2) # trigger level 0.2
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

ch_apdtime   = 0 # output channel 4
ch_apd       = 1 # output channel 4
ch_532       = 2 # output channel 0

n_runs = 30000

# sweep delta tau
delta_taus = np.linspace(0, 1000, 10)
for i, delta_tau in enumerate(delta_taus):

    seq_532 =     [(10000, HIGH), (delta_tau, LOW), (300, HIGH), (50000 - 10000 - 300 - delta_tau, LOW)]
    seq_apdtime = [(10000 - 300, LOW), (300, HIGH), (50000 - 10000, LOW) ]
    seq_apd =     [(10000 + delta_tau, LOW), (300, HIGH), (50000 - 10000 - 300 - delta_tau, LOW) ]

    seq = Sequence()
    seq.setDigital(ch_532, seq_532)
    seq.setDigital(ch_apdtime, seq_apdtime)
    seq.setDigital(ch_apd, seq_apd)

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
    seq.plot()
    print ("\nOutput running on Pulse Streamer")


    tagger.sync()
    hist = Histogram(tagger, CLICK_CH, START_CH, 10000, 5000) # bin width = 10 ns, 1000 bins

    time.sleep(.2) # give time tagger time to start
    pulser.stream(seq, n_runs, final) # start streaming pulses
    pause(3) # just set some number such that pulse stream finished by this time; 50 uS * 3000 runs = 0.15 sec.
    # n_run = 299792,

    data = hist.getData()
    ind  = hist.getIndex() # in pico seconds

    #plt.plot(ind, data)
    #plt.show()

    print("total counts:", np.sum(np.array(data)), "; length: ", len(data))

    if i == 0:
        data_container = np.vstack([ind, data])
    else:
        data_container = np.vstack([data_container, data])

columns = ['time (ps)'] + [str(int(t))+" (ns)" for t in delta_taus]
df = pd.DataFrame(data_container.T, columns = columns )
df.to_csv('data.csv', index = False)
