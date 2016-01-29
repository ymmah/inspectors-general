#!/usr/bin/env python

import datetime
import logging
import os
from urllib.parse import urljoin

from utils import utils, inspector

# https://www.flra.gov/OIG
archive = 1999

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

AUDIT_REPORTS_URL = "https://www.flra.gov/IG_audit-reports"
INTERNAL_REVIEWS_URL = "https://www.flra.gov/IG_internal-reviews"
QA_REVIEWS_URL = "https://www.flra.gov/OIG_QA_Reviews"
SEMIANNUAL_REPORTS_URL = "https://www.flra.gov/IG_semi-annual_reports"
PEER_REVIEWS_URL = "https://www.flra.gov/OIG-PEER-REVIEW"

REPORT_URLS = [
  ("audit", AUDIT_REPORTS_URL),
  ("inspection", INTERNAL_REVIEWS_URL),
  ("inspection", QA_REVIEWS_URL),
  ("semiannual_report", SEMIANNUAL_REPORTS_URL),
  ("peer_review", PEER_REVIEWS_URL),
]

REPORT_PUBLISHED_MAP = {
  "1014": datetime.datetime(2015, 6, 12),
  "886": datetime.datetime(2014, 7, 2),
  "757": datetime.datetime(2013, 8, 29),
  "756": datetime.datetime(2012, 11, 2),
  "931": datetime.datetime(2014, 9, 22),
  "505": datetime.datetime(2011, 6, 9),
  "451": datetime.datetime(2008, 9, 16),
  "612": datetime.datetime(2005, 4, 18),
  "613": datetime.datetime(2002, 4, 3),
  "1050": datetime.datetime(2015, 11, 16),
  "1058": datetime.datetime(2015, 12, 14),
  "1063": datetime.datetime(2016, 1, 20),
  "1059": datetime.datetime(2015, 12, 14),
  "945": datetime.datetime(2014, 11, 14),
  "963": datetime.datetime(2015, 1, 20),
  "949": datetime.datetime(2014, 12, 2),
  "1016": datetime.datetime(2015, 1, 1),
  "944": datetime.datetime(2014, 11, 14),
  "792": datetime.datetime(2013, 12, 6),
  "924": datetime.datetime(2013, 12, 6),
  "794": datetime.datetime(2013, 12, 18),
  "841": datetime.datetime(2014, 2, 24),
  "793": datetime.datetime(2013, 12, 18),
  "657": datetime.datetime(2012, 12, 15),
  "666": datetime.datetime(2012, 12, 30),
  "667": datetime.datetime(2012, 11, 30),
  "543": datetime.datetime(2011, 11, 15),
  "550": datetime.datetime(2011, 12, 28),
  "552": datetime.datetime(2011, 12, 28),
  "417": datetime.datetime(2010, 11, 15),
  "480": datetime.datetime(2010, 9, 30),
  "397": datetime.datetime(2009, 11, 13),
  "479": datetime.datetime(2009, 11, 15),
  "411": datetime.datetime(2009, 8, 14),
  "481": datetime.datetime(2009, 7, 9),
  "412": datetime.datetime(2007, 1, 1),
  "396": datetime.datetime(2005, 11, 14),
  "413": datetime.datetime(2004, 11, 12),
  "internalcontrolindpaud08": datetime.datetime(2008, 2, 8),
  "Audit-Report-FLRA-Security-Programs-(September-2004)---Non-Public-Report": datetime.datetime(2004, 9, 1),
  "03govveh": datetime.datetime(2003, 11, 30),
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  for report_type, url in REPORT_URLS:
    doc = utils.beautifulsoup_from_url(url)
    results = doc.select("div.node ul li")
    if not results:
      raise inspector.NoReportsFoundError("Federal Labor Relations Authority (%s)" % report_type)
    for result in results:
      report = report_from(result, url, report_type, year_range)
      if report:
        inspector.save_report(report)

def report_from(result, landing_url, report_type, year_range):
  title = result.text.strip()

  if 'Non-Public Report' in title:
    unreleased = True
    report_url = None
    report_id = "-".join(title.split())
    report_id = report_id.replace(":", "")
  else:
    unreleased = False
    link = result.find("a")
    if not link:
      return None
    # Some reports have incorrect relative paths
    relative_report_url = link.get('href').replace("../", "")
    report_url = urljoin(landing_url, relative_report_url)
    if report_url == "http://ignet.gov/internal/flra/03govveh.pdf":
      report_url = "https://www.flra.gov/webfm_send/395"
    report_filename = report_url.split("/")[-1]
    report_id, _ = os.path.splitext(report_filename)

  if (title == "Financial Statement Audit for Fiscal Year 2007" and
      report_id == "internalcontrolindpaud08"):
    # This link points to the wrong report, mark FY2007 financial statement
    # audit as unreleased
    report_id = "-".join(title.split())
    unreleased = True
    report_url = None

  published_on = None
  if report_id in REPORT_PUBLISHED_MAP:
    published_on = REPORT_PUBLISHED_MAP[report_id]
  if not published_on:
    try:
      published_on = datetime.datetime.strptime(title, '%B %Y')
    except ValueError:
      pass

  if not published_on:
    raise inspector.NoDateFoundError(report_id, title)

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'flra',
    'inspector_url': 'https://www.flra.gov/OIG',
    'agency': 'flra',
    'agency_name': 'Federal Labor Relations Authority',
    'file_type': 'pdf',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  if unreleased:
    report['unreleased'] = unreleased
    report['landing_url'] = landing_url
  return report

utils.run(run) if (__name__ == "__main__") else None
