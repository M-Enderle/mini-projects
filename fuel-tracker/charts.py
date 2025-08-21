import io
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict

import matplotlib
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.ticker import MaxNLocator

matplotlib.use('Agg')
sns.set_theme(style="whitegrid")


def _fig_to_png_bytes(fig) -> bytes:
	buf = io.BytesIO()
	fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
	plt.close(fig)
	buf.seek(0)
	return buf.getvalue()


def render_history(rows: List[Dict]) -> bytes:
	# rows: [{fuel, price, fetched_at, ...}]
	if not rows:
		fig, ax = plt.subplots(figsize=(6,3))
		ax.text(0.5, 0.5, 'Keine Daten', ha='center', va='center')
		ax.axis('off')
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
	fig, ax = plt.subplots(figsize=(6,3))
	for fuel, data in series.items():
		sns.lineplot(x=data['x'], y=data['y'], ax=ax, label=fuel)
	ax.set_xlabel('Zeit')
	ax.set_ylabel('€ / L')
	# Format x-axis to show exactly 5 ticks
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
	ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
	plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
	ax.legend().set_visible(False)
	sns.despine(fig=fig)
	return _fig_to_png_bytes(fig)


def render_bar(x_labels: List[str], y_values: List[float], title: str = '') -> bytes:
	fig, ax = plt.subplots(figsize=(6,3))
	sns.barplot(x=x_labels, y=y_values, ax=ax, color="#2563eb")
	ax.set_ylabel('€ / L')
	if title:
		ax.set_title(title)
	sns.despine(fig=fig)
	return _fig_to_png_bytes(fig)


def render_line(x_labels: List[str], y_values: List[float], title: str = '') -> bytes:
	fig, ax = plt.subplots(figsize=(6,3))
	sns.lineplot(x=x_labels, y=y_values, ax=ax, marker='o')
	ax.set_ylabel('€ / L')
	if title:
		ax.set_title(title)
	sns.despine(fig=fig)
	return _fig_to_png_bytes(fig) 