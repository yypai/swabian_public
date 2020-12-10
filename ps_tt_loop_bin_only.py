# for TimeTagger
from TimeTagger import setLogger, createTimeTagger, Combiner, Coincidence, Counter
from TimeTagger import Countrate, Correlation, TimeDifferences, TimeTagStream, Scope, Event
from TimeTagger import CHANNEL_UNUSED, UNKNOWN, LOW, HIGH, Histogram
from TimeTagger import DelayedChannel, GatedChannel, CountBetweenMarkers
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

CLICK_CH = 2 # the actual signal from APD or SNSPD
START_CH = 3
END_CH = DelayedChannel(tagger, START_CH, 100*1000) # 300 nS, unit is P

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


ch_532              = 1 # output channel 0
ch_apd_start        = 4 # output channel 4
#ch_apdtime          = 0 # output channel 4

n_runs = 1e5
pulse_period_ns = 50e3

# sweep delta tau
delta_taus = np.linspace(0, int(pulse_period_ns*0.02), 50)
print(delta_taus)
result = []
for i, delta_tau in enumerate(delta_taus):

    seq_532      =      [(10000,   HIGH),   (delta_tau, LOW),    (300, HIGH),      (pulse_period_ns - 10000 - 300 - delta_tau, LOW)]
    seq_apd_start =     [(10000  + 360 +  delta_tau, LOW),       (600, HIGH),      (pulse_period_ns - 10000 - 600 -360 - delta_tau, LOW) ]

    # fake APD signal; don't care
    # seq_apdtime  =      [(10000 - 300, LOW), (300, HIGH), (pulse_period_ns - 10000, LOW) ]

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
    count = CountBetweenMarkers(tagger, CLICK_CH, START_CH, END_CH.getChannel(), int(0.9*n_runs)) # bin width = 20 ns, 10000 bins 200 uS total

    time.sleep(.2) # give time tagger time to start
    pulser.stream(seq, n_runs, final) # start streaming pulses
    #pause(pulse_period_ns * 1e-9 * n_runs) # just set some number such that pulse stream finished by this time; 50 uS * 3000 runs = 0.15 sec.
    for _wait in range(int(n_runs/1000)+2):
        pause(pulse_period_ns * 1e-9 * n_runs/1000)
        print("dt:", delta_tau, "run:", _wait * 1000, end = '\r')

    data = count.getData()
    ind  = np.linspace(0, 1, int(0.9*n_runs))

    print("total counts:", np.sum(np.array(data)), "; length: ", len(data))
    result = result + [np.sum(np.array(data))]

columns = [int(t) for t in delta_taus]
print(result)
print(columns)

df = pd.DataFrame({"delay (ns)": columns,
                   "counts": result})
df.to_csv("NV_t1\{:%Y-%m-%d-%H-%M-%S%z}_nruns{:.0f}.csv".format(datetime.now(), n_runs), index = False)
