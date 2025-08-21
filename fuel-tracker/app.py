import os
import threading
import time
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, g, request, redirect, url_for, make_response

from database import get_db, init_db, close_db, fetch_stations, fetch_station_by_id, fetch_price_history
from fetcher import fetch_once_all, start_background_fetch_loop
from database import fetch_price_stats, fetch_stations_with_current_price
from charts import render_history, render_bar, render_line


def create_app() -> Flask:
	app = Flask(__name__)
	
	# Configure for reverse proxy
	from werkzeug.middleware.proxy_fix import ProxyFix
	app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

	# Ensure DB exists
	with app.app_context():
		init_db()

	# Register teardown
	@app.teardown_appcontext
	def _teardown_db(exception):  # noqa: ARG001
		close_db()

	@app.route("/")
	def index():
		stations = fetch_stations_with_current_price()
		return render_template("index.html", stations=stations)

	@app.route("/station/<station_id>")
	def station_detail(station_id: str):
		station = fetch_station_by_id(station_id)
		if not station:
			return redirect(url_for("index"))
		return render_template("station.html", station=station)

	@app.route("/api/stations")
	def api_stations():
		stations = fetch_stations()
		return jsonify([dict(row) for row in stations])

	@app.route("/api/station/<station_id>/history")
	def api_station_history(station_id: str):
		rows = fetch_price_history(station_id)
		return jsonify([dict(row) for row in rows])

	@app.route("/api/station/<station_id>/stats")
	def api_station_stats(station_id: str):
		return jsonify(fetch_price_stats(station_id))

	@app.route("/api/station/<station_id>/chart/<chart_type>.png")
	def api_station_chart(station_id: str, chart_type: str):
		if chart_type == "history":
			rows = [dict(r) for r in fetch_price_history(station_id)]
			png = render_history(rows)
		elif chart_type == "weekday":
			stats = fetch_price_stats(station_id)
			weekday_labels = ['So','Mo','Di','Mi','Do','Fr','Sa']
			x = [weekday_labels[int(r['weekday'])] for r in stats['avg_by_weekday']]
			y = [r['avg_price'] for r in stats['avg_by_weekday']]
			png = render_bar(x, y, '')
		elif chart_type == "hour":
			stats = fetch_price_stats(station_id)
			x = [str(r['hour']).zfill(2) for r in stats['avg_by_hour']]
			y = [r['avg_price'] for r in stats['avg_by_hour']]
			png = render_line(x, y, '')
		elif chart_type == "month":
			stats = fetch_price_stats(station_id)
			x = [r['month'] for r in stats['avg_by_month']]
			y = [r['avg_price'] for r in stats['avg_by_month']]
			png = render_line(x, y, '')
		elif chart_type == "min_day":
			stats = fetch_price_stats(station_id)
			x = [r['day'] for r in stats['min_by_day']]
			y = [r['min_price'] for r in stats['min_by_day']]
			png = render_line(x, y, '')
		else:
			return ("unknown chart", 404)
		resp = make_response(png)
		resp.headers.set('Content-Type', 'image/png')
		return resp

	@app.route("/fetch-now", methods=["POST"])  # Non-idempotent on purpose
	def fetch_now():
		# Trigger a synchronous one-off fetch
		count = fetch_once_all()
		return jsonify({"fetched": count, "timestamp": datetime.now(timezone.utc).isoformat()})

	# Start background loop
	start_background_fetch_loop()

	return app


app = create_app()


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=False) 