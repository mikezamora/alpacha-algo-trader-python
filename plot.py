import csv
import os
from random import random

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import ConciseDateFormatter

report_name_chart = 'output_chart.csv'
csv_file_chart = None
csv_writer_chart = None

plt.style.use('dark_background')

fig, ax1 = plt.subplots(figsize=(10, 5), layout='constrained')
cdf = ConciseDateFormatter(ax1.xaxis.get_major_locator())
ax1.xaxis.set_major_formatter(cdf)
ani = None
chart_data = []

for i in range(1,10):
    chart_data.append([random(), random(), random() ,random() ,random()])

def setup_animation():
    if os.path.exists(report_name_chart):
        os.remove(report_name_chart)
    else:
        print('{} does not exist, creating report file'.format(report_name_chart))
    
    csv_file_chart = open(report_name_chart, 'w', newline='')
    csv_writer_chart = csv.writer(csv_file_chart, dialect='excel', delimiter=',')

    # csv_writer_chart.writerow(['bid', 'ask', 'current', 'highest', 'lowest'])

    ani = animation.FuncAnimation(fig, animate, interval=1000)
    print('start animation')
    plt.show()

def animate(i):
    dataArray = chart_data

    x_bid = []
    y_bid = []

    x_ask = []
    y_ask = []

    x_current = []
    y_current = []

    x_high = []
    y_high = []

    x_low = []
    y_low = []

    index = 0
    for eachLine in dataArray:
        if len(eachLine)>1:
            bid,ask,current,highest,lowest = eachLine

            x_bid.append(index)
            y_bid.append(bid)
            x_ask.append(index)
            y_ask.append(ask)
            x_current.append(index)
            y_current.append(current)
            x_high.append(index)
            y_high.append(highest)
            x_low.append(index)
            y_low.append(lowest)

            index += 1

    ax1.clear()

    # make lines thicker and transparent
    ax1.plot(x_bid, y_bid, linewidth=2, linestyle=':', label='bid')
    ax1.plot(x_ask, y_ask, linewidth=2, linestyle=':', label='ask')
    ax1.plot(x_low, y_low, linewidth=2, linestyle='--', label='lowest')
    ax1.plot(x_high, y_high, linewidth=2, linestyle='--', label='highest')
    ax1.plot(x_current, y_current, linewidth=2, linestyle='-', label='current')
    ax1.legend()

setup_animation()