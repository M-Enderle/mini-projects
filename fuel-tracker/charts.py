import io
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict

import matplotlib
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.ticker import MaxNLocator

matplotlib.use('Agg')

# Custom style to match the website theme
plt.style.use('default')
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Playfair Display', 'Georgia', 'Times New Roman'],
    'font.size': 10,
    'axes.linewidth': 1,
    'axes.edgecolor': '#111111',
    'axes.labelcolor': '#111111',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.left': True,
    'axes.spines.bottom': True,
    'xtick.color': '#6b7280',
    'ytick.color': '#6b7280',
    'axes.axisbelow': True,
    'axes.grid': True,
    'grid.color': '#e5e7eb',
    'grid.linewidth': 0.5,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white'
})


def _fig_to_png_bytes(fig) -> bytes:
	buf = io.BytesIO()
	fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, 
	           facecolor='white', edgecolor='none')
	plt.close(fig)
	buf.seek(0)
	return buf.getvalue()


def render_history(rows: List[Dict]) -> bytes:
	# rows: [{fuel, price, fetched_at, ...}]
	if not rows:
		fig, ax = plt.subplots(figsize=(8,4))
		ax.text(0.5, 0.5, 'Keine Daten', ha='center', va='center', 
		        fontsize=14, color='#6b7280')
		ax.set_xlim(0, 1)
		ax.set_ylim(0, 1)
		ax.set_xticks([])
		ax.set_yticks([])
		return _fig_to_png_bytes(fig)
	
	# Split series by fuel
	series = {}
	for r in rows:
		fuel = r.get('fuel') or 'GAS'
		series.setdefault(fuel, {'x': [], 'y': []})
		# Truncate to seconds for parsing
		ts = r.get('fetched_at')
		try:
			dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
		except Exception:
			dt = None
		series[fuel]['x'].append(dt)
		series[fuel]['y'].append(r.get('price'))
	
	fig, ax = plt.subplots(figsize=(8,4))
	for fuel, data in series.items():
		ax.plot(data['x'], data['y'], color='#111111', linewidth=2, 
		        marker='o', markersize=3, label=fuel)
	
	ax.set_xlabel('Zeit', fontweight='600')
	ax.set_ylabel('€ / L', fontweight='600')
	
	# Format x-axis to show exactly 5 ticks
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
	ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
	plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
	
	if len(series) > 1:
		ax.legend(frameon=False, loc='upper left')
	
	return _fig_to_png_bytes(fig)


def render_bar(x_labels: List[str], y_values: List[float], title: str = '') -> bytes:
	fig, ax = plt.subplots(figsize=(8,4))
	bars = ax.bar(x_labels, y_values, color='#111111', alpha=0.8, width=0.6)
	
	ax.set_ylabel('€ / L', fontweight='600')
	if title:
		ax.set_title(title, fontweight='600', pad=20)
	
	# Add value labels on top of bars
	for bar, value in zip(bars, y_values):
		if value is not None:
			height = bar.get_height()
			ax.text(bar.get_x() + bar.get_width()/2., height + 0.001,
			        f'{value:.3f}', ha='center', va='bottom', fontsize=9, color='#6b7280')
	
	plt.xticks(rotation=45, ha='right')
	return _fig_to_png_bytes(fig)


def render_line(x_labels: List[str], y_values: List[float], title: str = '') -> bytes:
	fig, ax = plt.subplots(figsize=(8,4))
	ax.plot(x_labels, y_values, color='#111111', linewidth=2, 
	        marker='o', markersize=4, markerfacecolor='white', 
	        markeredgecolor='#111111', markeredgewidth=2)
	
	ax.set_ylabel('€ / L', fontweight='600')
	if title:
		ax.set_title(title, fontweight='600', pad=20)
	
	# Add value labels on points
	for i, (x, y) in enumerate(zip(x_labels, y_values)):
		if y is not None and i % max(1, len(x_labels) // 8) == 0:  # Show every nth label to avoid crowding
			ax.annotate(f'{y:.3f}', (x, y), textcoords="offset points", 
			           xytext=(0,10), ha='center', fontsize=8, color='#6b7280')
	
	plt.xticks(rotation=45, ha='right')
	return _fig_to_png_bytes(fig) 