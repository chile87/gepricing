from __future__ import annotations

from pathlib import Path
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlmodel import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = BACKEND_ROOT / "api"
for root in (BACKEND_ROOT, API_ROOT):
	if str(root) not in sys.path:
		sys.path.append(str(root))

from app.core.db import engine
from app.services.pricing_service import generate_recommendations, replace_market_data_from_mobile_file
from crawler.services.market_pipeline import collect_mobile_market_data


def run_market_pipeline() -> dict[str, object]:
	crawl_result = collect_mobile_market_data()
	with Session(engine) as session:
		imported = replace_market_data_from_mobile_file(session, crawl_result["outputFile"])
		generated = generate_recommendations(session, triggered_by="crawler")
	return {"crawl": crawl_result, "imported": imported, "generated": generated}


def main() -> None:
	scheduler = BlockingScheduler(timezone="Asia/Ho_Chi_Minh")
	scheduler.add_job(run_market_pipeline, "interval", minutes=30, id="mobile-market-pipeline", replace_existing=True)

	print("Running initial crawler -> importer -> rule engine pipeline...")
	initial_result = run_market_pipeline()
	print(initial_result)
	print("Scheduler started: reruns every 30 minutes.")
	scheduler.start()


if __name__ == "__main__":
	main()
