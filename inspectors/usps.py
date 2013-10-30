#!/usr/bin/env python

import utils
from bs4 import BeautifulSoup
from datetime import datetime

# options:
#   since - date (YYYY-MM-DD) to fetch reports from, or "all" to go back indefinitely.
#           defaults to 2 days ago.
#   only - limit reports fetched to one or more types, comma-separated. e.g. "audit,testimony"
#          can include:
#             audit - Audit Reports
#             testimony - Congressional Testimony
#             press - Press Releases
#             research - Risk Analysis Research Papers
#             interactive - SARC (Interactive)
#             congress - Semiannual Report to Congress
#          defaults to
#             including audits, reports to Congress, and research
#             excluding press releases, SARC, and testimony to Congress

def run(options):
  url = url_for(options)
  body = utils.download(url)
  doc = BeautifulSoup(body)

  results = doc.select(".views-row")
  for result in results:
    report = report_from(result)
    print "[%s][%s]" % (report['type'], report['published_on'])

    report['report_path'] = download_report(report)
    print "\treport: %s" % report['report_path']

    report['text_path'] = extract_report(report)
    print "\ttext: %s" % report['text_path']

    data_path = write_report(report)
    print "\tdata: %s" % data_path


# result is a BeautifulSoup elem
def report_from(result):
  report = {}

  pieces = result.select("span span")
  report_type = type_for(pieces[0].text.strip())

  if len(pieces) == 3:
    timestamp = pieces[2].text.strip()
    report['%s_id' % report_type] = pieces[1].text.strip()
  elif len(pieces) == 2:
    timestamp = pieces[1].text.strip()

  published_on = datetime.strptime(timestamp, "%m/%d/%Y")

  report['type'] = report_type
  report['published_on'] = datetime.strftime(published_on, "%Y-%m-%d")
  report['year'] = published_on.year

  # if there's only one button, use that URL
  # otherwise, look for "Read Full Report" (could be first or last)
  buttons = result.select("a.apbutton")
  if len(buttons) > 1:
    link = None
    for button in buttons:
      if "Full Report" in button.text:
        link = button['href']
  elif len(buttons) == 1:
    link = buttons[0]['href']
  report['url'] = link

  # get filename, use name as slug, extension for type
  filename = link.split("/")[-1]
  extension = filename.split(".")[-1]
  report['slug'] = filename.replace("." + extension, "")
  report['file_type'] = extension

  report['title'] = result.select("h3")[0].text.strip()

  return report


def download_report(report):
  report_path = "usps/%s/%s/report.%s" % (report['year'], report['slug'], report['file_type'])
  binary = (report['file_type'] == 'pdf')

  utils.download(
    report['url'],
    report_path,
    {'binary': binary}
  )
  return report_path

def extract_report(report):
  return utils.extract_text(report['report_path'])

def write_report(report):
  data_path = "usps/%s/%s/data.json" % (report['year'], report['slug'])
  utils.save(
    utils.json_for(report),
    data_path
  )
  return data_path

def type_for(original_type):
  original = original_type.lower()
  if "audit" in original:
    return "audit"
  elif "testimony" in original:
    return "testimony"
  elif "press release" in original:
    return "press"
  elif "research" in original:
    return "research"
  elif "sarc" in original:
    return "interactive"
  elif "report to congress":
    return "congress"
  else:
    return "unknown"

def url_for(options):
  url = "http://www.uspsoig.gov/document-library?"

  since = options.get('since', None)
  if since:
    url += "&field_doc_date_value[value][date]=%s" % since

  only = options.get('only', None)
  if not only:
    only = "audit,congress,research"
  only = only.split(",")
  params = ["field_doc_cat_tid[]=%s" % CATEGORIES[id] for id in only]
  url += "&%s" % str.join("&", params)

  return url


CATEGORIES = {
  'audit': '1920',
  'testimony': '1933',
  'press': '1921',
  'research': '1922',
  'interactive': '3487',
  'congress': '1923'
}

utils.run(run)