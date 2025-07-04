### Displays various graphs combaring junction reach attributes

import sys
sys.path.append('../') # This should probably be changed to a more sofisticated system at some point. i.e. install the package

import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import math

sns.set_theme()
sns.set_context('notebook', font_scale=1.5)
plt.tight_layout(pad=10);

JUNCTION_FILE = '../data/cleaned_data/reach_junctions.csv'

junctions = pd.read_csv(JUNCTION_FILE)
junctions = junctions.loc[ :, [
    'crime_reach', 'store_reach', 'transit_reach', 'rapid_transit_reach', 'schools_reach', 'retail_reach',
    'crime_count', 'stores_count', 'transit_count', 'rapid_transit_count', 'schools_count', 'retail_count',
]]

reaches = junctions.loc[ :, [
    'crime_reach', 'retail_reach', 'transit_reach', 'rapid_transit_reach', 'schools_reach'
]]

counts = junctions.loc[ :, [
    'crime_count', 'retail_count', 'transit_count', 'rapid_transit_count', 'schools_count'
]]

def coff_multi_corr(predictor, target):
    R_inv = np.linalg.inv(predictor.corr().to_numpy())
    
    combined = predictor.copy()
    combined['_target'] = target
    c = np.matrix(combined.corr()['_target'].drop('_target').to_numpy())
   
    r_sqr = (c * R_inv * np.transpose(c)).item()
    
    return r_sqr ** 0.5

corr = reaches.corr()
corr_count = counts.corr()
print(coff_multi_corr(reaches.loc[:, 'retail_reach':'schools_reach'], reaches['crime_reach']))


crime_reaches = junctions['crime_reach']
store_reaches = junctions['store_reach']
transit_reaches = junctions['transit_reach']
rtransit_reaches = junctions['rapid_transit_reach']
schools_reaches = junctions['schools_reach']
retail_reaches = junctions['retail_reach']

crime_counts = junctions['crime_count']
store_counts = junctions['stores_count']
transit_count = junctions['transit_count']
rtransit_count = junctions['rapid_transit_count']
schools_count = junctions['schools_count']
retail_count = junctions['retail_count']

use_reach = False
label_names = "Reach" if use_reach else "Count"

crime_data = crime_reaches #crime_reaches if use_reach else crime_counts
store_data = store_reaches if use_reach else store_counts
transit_data = transit_reaches if use_reach else transit_count
rtransit_data = rtransit_reaches if use_reach else rtransit_count
schools_data = schools_reaches if use_reach else schools_count
retail_data = retail_reaches if use_reach else retail_count

def hist_mean(x_data, y_data, bin_count):
    bins = [[0,0] for _ in range(bin_count)]
    min_x, max_x = min(x_data), max(x_data)
    width = (max_x - min_x) / bin_count
    
    for i in range(len(x_data)):
        index = math.floor((x_data[i] - min_x) / width)
        index = min(index, bin_count - 1) # The max value results in an index of bin_count
        bins[index][1] += y_data[i]
        bins[index][0] += 1
        
    bins_x = [min_x + width * i for i in range(bin_count)]
    bins_y = [b[1] / b[0] if b[0] else 0 for b in bins]
    
    bins_count_norm = [b[0] for b in bins]
    bins_count_norm = [b / max(bins_count_norm) for b in bins_count_norm]
    
    return bins_x, bins_y, bins_count_norm, width

def analyze(ax: plt.Axes, data, xlabel, ylabel):
    
    # Get and sort the data
    x_data, y_data = data
    sort = x_data.argsort()
    x_data = x_data[sort]
    y_data = y_data[sort]
    
    bins_x, bins_y, bins_count, width = hist_mean(x_data, y_data, 16)
    
    # Plot the data
    ax.scatter(x_data, y_data)
    # ax.bar(bins_x, bins_count, width=width, align='edge', color="purple", alpha=0.5)
    # ax.step([*bins_x, max(x_data)], [*bins_y, bins_y[-1]], where="post", color="green", linewidth=3)
    ax.plot(np.unique(x_data), np.poly1d(np.polyfit(x_data, y_data, 1))(np.unique(x_data)), color="red", linewidth=3)

    # ax.vlines([np.mean(x_data)], 0, 1, color='green', linewidth=3)
    # ax.vlines([np.mean(x_data) + np.std(x_data)], 0, 1, color='red', linewidth=3)
    
    print(f'{xlabel} - {ylabel} Correlation Coefficient: {np.corrcoef(x_data, y_data)[1,0]:.3f}')
    
    # Label the plot
    ax.set_ylabel(f'{ylabel} {label_names}')
    ax.set_xlabel(f'{xlabel} {label_names}')
    # ax.get_yaxis().set_visible(False)
  
# analyze(plt.subplot(2, 2, 1), (crime_data, crime_data), 'Crime', 'Crime')  
analyze(plt.subplot(2, 2, 1), (retail_data, crime_data), 'Retail', 'Crime')  
analyze(plt.subplot(2, 2, 2), (transit_data, crime_data), 'Transit', 'Crime')  
analyze(plt.subplot(2, 2, 3), (rtransit_data, crime_data), 'Rapid Transit', 'Crime')  
analyze(plt.subplot(2, 2, 4), (schools_data, crime_data), 'School', 'Crime')  
# analyze(plt.subplot(2, 2, 4), (employees_data, crime_data), 'Employees', 'Crime')
# sns.heatmap(round(corr, 2), annot=True, cmap='coolwarm', fmt='.2f', linewidths=.05, ax=plt.subplot(2, 2, 2))
# sns.heatmap(round(corr_count, 2), annot=True, cmap='coolwarm', fmt='.2f', linewidths=.05, ax=plt.subplot(2, 2, 2))

plt.show()