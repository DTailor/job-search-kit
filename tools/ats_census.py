"""ATS census for wide discovery: enumerate employer job boards, cache their public postings, triage offline.

  python3 tools/ats_census.py enumerate --run DIR [--seed FILE ...] [--scan DIR ...]
  python3 tools/ats_census.py fetch     --run DIR [--providers a,b] [--refresh] [--limit N]
  python3 tools/ats_census.py triage    --run DIR [--dedup FILE ...] [--exclude FILE ...]
  python3 tools/ats_census.py digest    --run DIR [--scope ...] [--dedup new] [--skip-flag ...] [--offset N --count M]
  python3 tools/ats_census.py show      --run DIR KEY [KEY ...]      # KEY = substring of "slug::title"
  python3 tools/ats_census.py funnel    --run DIR

Read-only: GET requests to public job-board APIs and the public Common Crawl URL index. No accounts,
no forms, no personal data in any request. Stdlib only.

Design (why this replaced the per-run census script):
- fetch caches the body of every engineering-titled posting that mentions a configured skill, whatever its
  location label. Location, contract and scope rules run offline in `triage`, so changing a rule never
  needs a refetch, and every dropped row is written to drops.jsonl with its reason.
- triage extracts hiring-region evidence from the body (not only the location label) and splits the pool
  into home / region / remote-unknown / countries-only / elsewhere, with the deciding sentence quoted.
- Person-specific vocabulary (skills, home country, region) is required configuration: it comes from
  <paths.profile>/census.json in the workspace or RUN/census-config.json. The title and place lists
  below are overridable defaults (the place lists are Europe-centred).

A census row is a discovery lead. Read the body, apply the gates in profile/PREFERENCES.md and verify the
posting on the employer's page before retaining it.
"""
import argparse
import gzip
import html
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/18.0 Safari/605.1.15")
lock = threading.RLock()  # re-entrant: log() is called while the lock is held

# ---------------------------------------------------------------- configuration
DEFAULTS = {
    # Common Crawl crawl ids to read, newest first. Check https://index.commoncrawl.org/collinfo.json.
    "crawls": [],
    # Required, person-specific (set them in <paths.profile>/census.json or RUN/census-config.json):
    #   skills: what the person works in, e.g. [r"\\bpython\\b", r"\\bdjango\\b"]
    #   home:   the country (and its cities) the person works from
    #   region: the wider area a remote role may name, e.g. ["europe", r"\\bemea\\b", r"\\bcet\\b"]
    "skills": [], "home": [], "region": [],
    # Optional: regexes for places inside / outside the region. The built-in lists below are Europe-centred.
    "region_places": None, "outside_places": None,
    # Titles kept at fetch time (loose on purpose; scope is decided offline).
    "title_keep": r"engineer|developer|programmer|back-?\s?end|software|python|django|fastapi|\bapis?\b|integration|"
                  r"platform|full-?\s?stack|entwickler|ingenieur|desarrollador|programista|dezvoltator|inżynier|"
                  r"d[ée]veloppeu|sviluppatore|ontwikkelaar|utvecklare|architect|tech(nical)? lead",
    "title_never": r"\bsales\b|account (exec|manag)|recruit|marketing|\bintern\b|internship|working student|werkstudent|"
                   r"praktik|trainee|apprentice|mechanical|electrical|civil|hardware|\brf\b|manufactur|process engineer|"
                   r"field service|maintenance|technician|chemical|quality engineer|structural|construction",
    # Offline scope rules (title level). A title naming a skill is never dropped by title_out_unless_skill.
    "title_out": r"\bjunior\b|\bjr\b|graduate|entry[- ]level|\bqa\b|quality assurance|\bsdet\b|test(ing)? engineer|tester|"
                 r"\bmanager\b|director|head of|\bvp\b|vice president|designer|\bios\b|android|\bmobile\b|embedded|firmware|"
                 r"data scientist|research scientist|\banalyst\b|support engineer|solutions? engineer|sales engineer|"
                 r"customer success|security engineer|devsecops|network engineer|\bdba\b|scrap|blockchain|solidity|"
                 r"smart contract|\bgame\b|robotic|perception|compiler|kernel|\bgpu\b|\bhpc\b|annotat|ai train|"
                 r"\bfront-?\s?end\b(?!.{0,25}back)",
    "title_out_unless_skill": r"data engineer|analytics engineer|machine learning|\bml\b|mlops|\bai engineer\b|applied ai|"
                              r"\bai/ml\b|infrastructure|\binfra\b|reliability|\bsre\b|devops|cloud engineer|"
                              r"forward deployed|\bjava\b|golang|\bgo\b|\bruby\b|\brails\b|\bphp\b|\bnode|typescript|"
                              r"\bkotlin\b|\bscala\b|\brust\b|\.net\b|c#|c\+\+|\bswift\b|elixir|salesforce|\bsap\b",
    "other_languages": r"\b(go|golang|java|kotlin|ruby|rails|node\.?js|typescript|rust|scala|elixir|php|c#|\.net|c\+\+)\b",
    "level_out": r"\b(junior|mid[- ]?level|intermediate|associate|graduate|entry)\b",
}

EU_PLACES = re.compile(
    r"germany|deutschland|berlin|munich|münchen|hamburg|frankfurt|cologne|köln|stuttgart|austria|vienna|wien|switzerland|"
    r"zurich|zürich|geneva|basel|netherlands|amsterdam|rotterdam|utrecht|eindhoven|belgium|brussels|antwerp|ghent|france|"
    r"paris|lyon|toulouse|spain|madrid|barcelona|valencia|malaga|málaga|portugal|lisbon|lisboa|porto|italy|milan|rome|turin|"
    r"ireland|dublin|cork|united kingdom|\buk\b|\bgb\b|england|scotland|wales|london|manchester|edinburgh|bristol|cambridge|"
    r"oxford|leeds|glasgow|poland|warsaw|krak|wroc|gdansk|gdańsk|pozna|łódź|czech|prague|brno|slovakia|bratislava|"
    r"hungary|budapest|bulgaria|sofia|greece|athens|thessaloniki|croatia|zagreb|serbia|belgrade|novi sad|slovenia|ljubljana|"
    r"lithuania|vilnius|kaunas|latvia|riga|estonia|tallinn|finland|helsinki|sweden|stockholm|gothenburg|malmö|norway|oslo|"
    r"denmark|copenhagen|aarhus|luxembourg|cyprus|limassol|nicosia|malta|ukraine|kyiv|lviv|moldova|chisinau|georgia|tbilisi|"
    r"armenia|yerevan|turkey|istanbul|iceland|albania|tirana|bosnia|sarajevo|montenegro|macedonia|skopje|kosovo|"
    r", (de|fr|es|it|nl|be|pl|pt|at|ch|ie|gb|se|no|dk|fi|cz|sk|hu|bg|gr|hr|rs|si|lt|lv|ee|lu|cy|mt|ua)$", re.I)
NON_EU = re.compile(
    r"united states|\busa\b|\bus\b|u\.s\.|new york|nyc|san francisco|\bsf\b|bay area|seattle|austin|boston|chicago|"
    r"los angeles|denver|atlanta|miami|toronto|vancouver|montreal|canada|mexico|brazil|brasil|são paulo|sao paulo|argentina|"
    r"buenos aires|colombia|bogot|chile|peru|costa rica|latam|latin america|americas|north america|india|bangalore|bengaluru|"
    r"hyderabad|pune|mumbai|delhi|gurgaon|gurugram|noida|chennai|kolkata|singapore|australia|sydney|melbourne|new zealand|"
    r"auckland|japan|tokyo|korea|seoul|china|shanghai|beijing|hong kong|taiwan|taipei|philippines|manila|vietnam|indonesia|"
    r"jakarta|malaysia|kuala lumpur|thailand|bangkok|pakistan|lahore|karachi|bangladesh|nigeria|lagos|kenya|nairobi|"
    r"south africa|cape town|johannesburg|egypt|cairo|israel|tel aviv|dubai|\buae\b|saudi|riyadh|qatar|doha|apac|"
    r", (in|us|ca|jp|my|ph|pe|au|nz|sg|cn|tw|br|mx|ar|co|cl|za|ng|ke|eg|il|ae|sa|ma|kr|vn|id|th|pk)$", re.I)
US_STATES = re.compile(
    r",\s?(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|"
    r"RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b|\b(Alabama|Arizona|California|Colorado|Connecticut|Florida|Illinois|Indiana|"
    r"Maryland|Massachusetts|Michigan|Minnesota|Missouri|Nevada|New Jersey|North Carolina|Ohio|Oregon|Pennsylvania|"
    r"Tennessee|Texas|Utah|Virginia|Washington|Wisconsin)\b")
REMOTE = re.compile(r"remote|anywhere|worldwide|distributed|work from home|wfh|telearbeit|home ?office|zdaln|la distan"
                    r"|télétravail|teletrabajo", re.I)

# Body evidence. Each pattern yields a quoted sentence in the triage output.
US_ONLY = re.compile(
    r"(must|should|need to) (be |currently )?(located|based|reside|residing|live|living)[^.\n]{0,40}"
    r"(united states|\bus\b|u\.s\.|usa|canada|north america)|"
    r"(authori[sz]ed|authori[sz]ation|eligible|legally (able|authori[sz]ed)|right) to work in the (united states|us\b|u\.s\.)|"
    r"us citizen|u\.s\. citizen|security clearance|(us|u\.s\.|usa|united states)[- ]based|within the (us|united states|u\.s\.)\b|"
    r"remote[^.\n]{0,25}\(?(us|usa|united states|u\.s\.)( only)?\)?(?![a-z])|anywhere in the (us|u\.s\.|united states)|"
    r"\b401\s?\(?k\)?|medical, dental,? (and|&) vision|(this|the) role is (only )?open to[^.\n]{0,40}(us|united states|canada)|"
    r"we (are|can) (only |currently )?(hire|hiring|able to hire)[^.\n]{0,50}(united states|\bus\b|u\.s\.|following states)|"
    r"(pst|pt|est|et|cst|pacific|eastern|central) (time|hours|time zone|business hours)|sponsor(ship)?[^.\n]{0,30}(h-?1b|visa)", re.I)
ELSEWHERE_ONLY = re.compile(
    r"(must|should|need to|required to) (be |currently )?(based|located|reside|residing|live|living)[^.\n]{0,25}"
    r"in (the )?(uk|united kingdom|germany|france|spain|netherlands|poland|portugal|ireland|israel|india|brazil|latam|"
    r"latin america|canada|australia|sweden|denmark|italy|switzerland|austria|belgium)|"
    r"right to work in (the )?(uk|united kingdom|germany|ireland|netherlands|france|spain)|"
    r"(uk|german|french|spanish|dutch|polish|irish)[- ](based|resident|residents|citizens)( only)?\b|"
    r"(latam|latin america|india|apac|asia)[- ](based|only)", re.I)
ONSITE = re.compile(
    r"relocat(e|ion) (to|is required)|hybrid[^.\n]{0,40}(\d ?(days|x)|office)|\d (days|times) (a|per) week (in|at|from) (the|our) office|"
    r"on-?site (in|at|role|position|presence)|in[- ]office \d|office[- ]based|this is not a remote", re.I)
EMPLOYEE = re.compile(
    r"permanent (employment|contract|position|role)|employment contract|unbefristet|festanstellung|contrat (de travail|cdi)|"
    r"\bcdi\b|umowa o prac|\bcim\b|full-time employee|employer of record|\beor\b|"
    r"(via|through) (deel|remote\.com|oyster|omnipresent|papaya)", re.I)
B2B = re.compile(
    r"\bb2b\b(?! (saas|software|product|platform|compan|payment|market|fintech|customer|client|sales|commerce|e-?commerce|"
    r"business|solution|startup|space|tech|brand|segment|buyer|marketplace|and b2c|or b2c|/b2c))|"
    r"independent contractor|as an? (independent |external )?contractor|contractor (agreement|basis|role|position|status|contract)|"
    r"freelanc|freiberuf|contract (role|position|basis|engagement|duration|length|type)|"
    r"\b\d{1,2}[- ]months?( rolling| initial| fixed[- ]term)? contract|contract[^.\n]{0,25}(extension|extendable|renewable|long[- ]term)|"
    r"(day|daily|hourly) rate|per (day|hour)\b|/ ?(hour|hr|day)\b|self-employed|\bpfa\b|\bsrl\b|\bc2c\b|corp[- ]to[- ]corp|"
    r"outside ir35|sole trader|own (company|legal entity)|umowa b2b|kontrakt", re.I)
ONCALL = re.compile(r"on-?call|pager ?duty|out[- ]of[- ]hours|24/7|\brota\b|after[- ]hours", re.I)
LEAD_REQ = re.compile(r"(experience|previous|proven)[^.\n]{0,40}(as a|in a) (staff|principal|tech(nical)? lead|lead) (engineer|role)|"
                      r"(staff|principal)[- ]level experience", re.I)
LLM_REQ = re.compile(r"(experience|expertise|track record|background)[^.\n]{0,60}(llm|large language|rag\b|agentic|ai agents?|"
                     r"langchain|prompt engineering|fine-?tun)|(llm|rag|agentic|ai agents?)[^.\n]{0,40}(in production|required)", re.I)
FRONTEND = re.compile(r"\breact\b|\bvue\b|\bangular\b|next\.js|\bfrontend\b|\bfront-end\b|\bcss\b", re.I)
PAY = re.compile(r"(€|eur|\$|usd|£|gbp|chf|pln|ron)\s?\d[\d.,]*\s?(k|000)?[^.\n]{0,40}", re.I)
SENIOR = re.compile(r"\bsenior\b|\bsr\.?\b|\bstaff\b|\blead\b|\bprincipal\b|\bexpert\b|\bIII\b|\bL[4-6]\b|seni[oó]r|starszy", re.I)
SECTION = re.compile(r"(requirements?|qualifications?|what you('ll| will)? (bring|need)|you have|about you|must[- ]haves?|"
                     r"who you are|your profile|what we('re| are) looking for|skills? (and|&) experience|dein profil|"
                     r"what you('ll| will) do|responsibilities|the role)\s*:?\s*\n", re.I)


def load_config(run):
    cfg = dict(DEFAULTS)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import workspace
        p = workspace.root() / workspace.load()["paths"].get("profile", "profile") / "census.json"
        if p.is_file():
            cfg.update(json.loads(p.read_text()))
    except Exception:
        pass
    local = Path(run) / "census-config.json"
    if local.is_file():
        cfg.update(json.loads(local.read_text()))
    return cfg


def rx(v):
    return re.compile("|".join(v) if isinstance(v, list) else v, re.I)


class Run:
    def __init__(self, run):
        self.dir = Path(run).resolve()
        self.cc = self.dir / "raw" / "cc"
        self.boards_dir = self.dir / "raw" / "boards2"
        for d in (self.cc, self.boards_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.cfg = load_config(self.dir)
        self.logf = open(self.dir / "census.log", "a")
        c = self.cfg
        missing = [k for k in ("skills", "home", "region") if not c.get(k)]
        if missing:
            raise SystemExit(f"ats_census: set {', '.join(missing)} in <paths.profile>/census.json or {self.dir}/census-config.json "
                             "(lists of case-insensitive regex fragments; see DEFAULTS in this file)")
        self.SKILL, self.HOME, self.REGION = rx(c["skills"]), rx(c["home"]), rx(c["region"])
        self.IN_REGION = rx(c["region_places"]) if c.get("region_places") else EU_PLACES
        self.OUTSIDE = rx(c["outside_places"]) if c.get("outside_places") else NON_EU
        self.KEEP, self.NEVER = rx(c["title_keep"]), rx(c["title_never"])
        self.OUT, self.OUT_UNLESS = rx(c["title_out"]), rx(c["title_out_unless_skill"])
        self.OTHER, self.LEVEL = rx(c["other_languages"]), rx(c["level_out"])
        r = "|".join(c["region"]) if isinstance(c["region"], list) else c["region"]
        h = "|".join(c["home"]) if isinstance(c["home"], list) else c["home"]
        self.REGION_REMOTE = re.compile(
            rf"(remote|anywhere|work from|based|located|hire|hiring|candidates|open to|applicants)[^.\n]{{0,90}}({r}|{h})|"
            rf"({r}|{h})[^.\n]{{0,70}}(remote|time ?zones?|based|candidates|only)", re.I)

    def log(self, *a):
        s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
        with lock:
            self.logf.write(s + "\n"); self.logf.flush()
            print(s, flush=True)


def get(url, timeout=40, headers=None, tries=1, data=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/xml, */*", "Accept-Encoding": "gzip"}
    if headers:
        h.update(headers)
    last = (0, "")
    for i in range(tries):
        req = urllib.request.Request(url, headers=h, data=data)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = (e.code, "")
            if e.code in (404, 410, 401, 403):
                return last
            if e.code == 429:
                time.sleep(20 + random.random() * 20)
        except Exception as e:
            last = (0, f"{type(e).__name__}: {e}")
        if i < tries - 1:
            time.sleep(min(60, 4 * (2 ** i)) + random.random() * 3)
    return last


def strip_html(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


# ---------------------------------------------------------------- enumerate
CC_QUERIES = {
    "ashby": ["url=jobs.ashbyhq.com/*"],
    "greenhouse": ["url=job-boards.greenhouse.io/*", "url=boards.greenhouse.io/*", "url=job-boards.eu.greenhouse.io/*"],
    "lever": ["url=jobs.lever.co/*", "url=jobs.eu.lever.co/*"],
    "recruitee": ["url=recruitee.com&matchType=domain"],
    "personio": ["url=jobs.personio.de&matchType=domain", "url=jobs.personio.com&matchType=domain"],
    "teamtailor": ["url=teamtailor.com&matchType=domain"],
    "smartrecruiters": ["url=jobs.smartrecruiters.com/*", "url=careers.smartrecruiters.com/*"],
    "rippling": ["url=ats.rippling.com/*"],
    "breezy": ["url=breezy.hr&matchType=domain"],
    "pinpoint": ["url=pinpointhq.com&matchType=domain"],
    "workable": ["url=apply.workable.com/*"],
}
# Any text file can seed slugs (old scout evidence, investor-board exports, search results).
SLUG_PATTERNS = [
    ("ashby", r"jobs\.ashbyhq\.com/([A-Za-z0-9._%-]+)"),
    ("greenhouse", r"(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_(?:board|app)(?:/js)?\?(?:[^\s\"']*&)?for=)?([A-Za-z0-9_-]+)"),
    ("lever_eu", r"jobs\.eu\.lever\.co/([A-Za-z0-9._-]+)"),
    ("lever", r"jobs\.lever\.co/([A-Za-z0-9._-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9._-]+)"),
    ("rippling", r"ats\.rippling\.com/([A-Za-z0-9._-]+)"),
    ("workable", r"apply\.workable\.com/([A-Za-z0-9._-]+)"),
    ("recruitee", r"([a-z0-9-]+)\.recruitee\.com"),
    ("personio", r"([a-z0-9-]+)\.jobs\.personio\.(?:de|com)"),
    ("teamtailor", r"([a-z0-9-]+)\.teamtailor\.com"),
    ("breezy", r"([a-z0-9-]+)\.breezy\.hr"),
    ("pinpoint", r"([a-z0-9-]+)\.pinpointhq\.com"),
]
CASE_SENSITIVE = {"ashby", "lever", "lever_eu", "smartrecruiters", "rippling"}
BAD_SLUGS = {"", "api", "embed", "static", "assets", "favicon.ico", "robots.txt", "sitemap.xml", "www", "app", "careers",
             "jobs", "job", "apply", "login", "signin", "privacy", "terms", "help", "support", "blog", "static-assets",
             "cdn", "images", "img", "js", "css", "fonts", "en", "de", "fr", "es", "it", "nl", "pl", "pt", "sv", "da",
             "fi", "no", "cs", "ro", "hu", "jobs-api", "search", "posting-api", "v1", "v2", "v3", "admin", "my", "candidate",
             "connect", "mail", "status", "docs", "developers", "partners", "integrations", "marketplace", "career",
             "go", "boards", "board", "widget", "portal", "_next", "public", "ats", "hire", "oauth", "auth", "j", "view",
             "embed.js", "info", "landing", "cookies", "sso", "job_board", "job_app", "internal"}


def slugs_in(text):
    out = set()
    for provider, pat in SLUG_PATTERNS:
        for m in re.finditer(pat, text):
            s = unquote(m.group(1)).strip(".")
            if provider not in CASE_SENSITIVE:
                s = s.lower()
            if s.lower() not in BAD_SLUGS and 1 < len(s) < 80:
                out.add((provider, s))
    return out


def cmd_enumerate(R, args):
    crawls = args.crawls.split(",") if args.crawls else R.cfg["crawls"]
    if not crawls:
        st, b = get("https://index.commoncrawl.org/collinfo.json", tries=4, timeout=60)
        crawls = [c["id"] for c in json.loads(b)[:3]] if st == 200 else []
        R.log("crawls from collinfo:", crawls)
    slugs, status = set(), []
    # cached pages from any crawl (also ones no longer in the crawl list) always count
    for fp in R.cc.glob("*.txt"):
        slugs |= slugs_in(fp.read_text(errors="replace"))
    R.log("slugs from cached crawl pages:", len(slugs))
    providers = args.providers.split(",") if args.providers else list(CC_QUERIES)
    for provider in providers:
        for q in CC_QUERIES.get(provider, []):
            for crawl in crawls:
                key = re.sub(r"[^A-Za-z0-9]+", "_", f"{crawl}_{q}")
                meta = R.cc / (key + ".pages")
                if meta.exists():
                    n = int(meta.read_text())
                else:
                    st, b = get(f"https://index.commoncrawl.org/{crawl}-index?{q}&output=json&fl=url&showNumPages=true", timeout=90, tries=5)
                    try:
                        n = json.loads(b).get("pages", 0) if st == 200 else None
                    except Exception:
                        n = None
                    if n is None:
                        R.log("CC pages FAILED", crawl, q, st)
                        status.append(dict(provider=provider, q=q, crawl=crawl, state="pages_failed"))
                        continue
                    meta.write_text(str(n))
                got = 0
                for p in range(n):
                    fp = R.cc / f"{key}_p{p}.txt"
                    if not fp.exists():
                        st, b = get(f"https://index.commoncrawl.org/{crawl}-index?{q}&output=json&fl=url&page={p}", timeout=180, tries=5)
                        if st != 200:
                            R.log("CC page FAILED", crawl, q, p, st)
                            status.append(dict(provider=provider, q=q, crawl=crawl, page=p, state=f"page_failed_{st}"))
                            continue
                        urls = []
                        for line in b.splitlines():
                            try:
                                urls.append(json.loads(line)["url"])
                            except Exception:
                                pass
                        fp.write_text("\n".join(urls))
                        slugs |= slugs_in("\n".join(urls))
                        time.sleep(1.5)
                    got += 1
                status.append(dict(provider=provider, q=q, crawl=crawl, pages=n, pages_read=got, state="ok" if got == n else "partial"))
                R.log("CC", provider, crawl, q, f"{got}/{n} pages; slugs so far", len(slugs))
    for seed in args.seed or []:
        try:
            for b in json.loads(Path(seed).read_text()):
                slugs.add((b.get("provider") or b.get("kind"), b["slug"]))
        except Exception:
            slugs |= slugs_in(Path(seed).read_text(errors="replace"))
    for d in args.scan or []:
        n0 = len(slugs)
        for fp in Path(d).rglob("*"):
            if fp.is_file() and fp.suffix.lower() in (".json", ".jsonl", ".txt", ".md", ".html", ".csv", ".xml") and fp.stat().st_size < 40_000_000:
                if R.dir in fp.parents and "boards" in fp.parts:
                    continue
                try:
                    slugs |= slugs_in(fp.read_text(errors="replace"))
                except Exception:
                    pass
        R.log("scan", d, "added", len(slugs) - n0)
    seen, boards = set(), []
    for p, s in sorted(x for x in slugs if x[0]):
        k = (p, s.lower())
        if k in seen:
            continue
        seen.add(k); boards.append(dict(provider=p, slug=s))
    (R.dir / "boards2.json").write_text(json.dumps(boards))
    (R.dir / "cc-status.json").write_text(json.dumps(status, indent=1))
    R.log("ENUMERATED", len(boards), dict(Counter(b["provider"] for b in boards)))


# ---------------------------------------------------------------- fetch
def board_fetch(provider, slug):
    """(status, [job dict]). desc is None when the list feed has no body and a detail call is needed."""
    jobs = []
    if provider == "ashby":
        st, b = get(f"https://api.ashbyhq.com/posting-api/job-board/{quote(slug)}?includeCompensation=true", tries=3)
        if st != 200:
            return st, []
        for j in json.loads(b).get("jobs", []):
            locs = [j.get("location") or ""] + [x.get("location", "") for x in j.get("secondaryLocations") or []]
            addr = ((j.get("address") or {}).get("postalAddress") or {})
            if addr.get("addressCountry"):
                locs.append(addr["addressCountry"])
            jobs.append(dict(id=j.get("id"), title=j.get("title"), url=j.get("jobUrl"), locs=[l for l in locs if l],
                             wp=j.get("workplaceType") or ("Remote" if j.get("isRemote") else ""), posted=(j.get("publishedAt") or "")[:10],
                             etype=j.get("employmentType") or "", comp=((j.get("compensation") or {}).get("compensationTierSummary") or ""),
                             desc=j.get("descriptionPlain") or strip_html(j.get("descriptionHtml") or "")))
        return 200, jobs
    if provider in ("greenhouse", "greenhouse_eu"):
        # EU boards are served by the main API host. content=true returns every body in one call.
        st, b = get(f"https://boards-api.greenhouse.io/v1/boards/{quote(slug)}/jobs?content=true", tries=3, timeout=120)
        if st != 200:
            return st, []
        for j in json.loads(b).get("jobs", []):
            locs = [(j.get("location") or {}).get("name") or ""] + [o.get("name", "") for o in j.get("offices") or []]
            jobs.append(dict(id=j.get("id"), title=j.get("title"), url=j.get("absolute_url"), locs=[l for l in locs if l], wp="",
                             posted=(j.get("first_published") or j.get("updated_at") or "")[:10], etype="", comp="",
                             desc=strip_html(html.unescape(j.get("content") or ""))))
        return 200, jobs
    if provider in ("lever", "lever_eu"):
        host = "api.eu.lever.co" if provider == "lever_eu" else "api.lever.co"
        st, b = get(f"https://{host}/v0/postings/{quote(slug)}?mode=json", tries=3)
        if st != 200:
            return st, []
        for j in json.loads(b):
            c = j.get("categories") or {}
            locs = [c.get("location") or ""] + list(c.get("allLocations") or [])
            desc = (j.get("descriptionPlain") or "") + "\n" + "\n".join(
                (x.get("text", "") + "\n" + strip_html(x.get("content", ""))) for x in j.get("lists") or []) + "\n" + (j.get("additionalPlain") or "")
            sr = j.get("salaryRange") or {}
            comp = f"{sr.get('currency','')} {sr.get('min','')}-{sr.get('max','')} {sr.get('interval','')}" if sr else ""
            jobs.append(dict(id=j.get("id"), title=j.get("text"), url=j.get("hostedUrl"), locs=[l for l in locs if l],
                             wp=j.get("workplaceType") or "", posted=time.strftime("%Y-%m-%d", time.gmtime((j.get("createdAt") or 0) / 1000)),
                             etype=c.get("commitment") or "", comp=comp, desc=desc))
        return 200, jobs
    if provider == "recruitee":
        st, b = get(f"https://{slug}.recruitee.com/api/offers/", tries=3)
        if st != 200:
            return st, []
        for j in json.loads(b).get("offers", []):
            locs = [j.get("location") or "", j.get("country") or "", j.get("city") or ""] + [
                (l.get("name") or "") + " " + (l.get("country") or "") for l in j.get("locations") or []]
            wp = "Remote" if j.get("remote") else ("Hybrid" if j.get("hybrid") else ("OnSite" if j.get("on_site") else ""))
            sal = j.get("salary") or {}
            comp = f"{sal.get('currency','')} {sal.get('min','')}-{sal.get('max','')} {sal.get('period','')}" if sal and sal.get("min") else ""
            jobs.append(dict(id=j.get("id"), title=j.get("title"), url=j.get("careers_url"), locs=[l.strip() for l in locs if l and l.strip()], wp=wp,
                             posted=(j.get("published_at") or j.get("created_at") or "")[:10], etype=j.get("employment_type_code") or "",
                             comp=comp, desc=strip_html((j.get("description") or "") + "\n" + (j.get("requirements") or ""))))
        return 200, jobs
    if provider == "personio":
        st, b, dom = 0, "", "de"
        for dom in ("de", "com"):
            st, b = get(f"https://{slug}.jobs.personio.{dom}/xml?language=en", tries=2)
            if st == 200 and "<workzag-jobs" in b:
                break
        else:
            return (st if st != 200 else -1), []
        try:
            root = ET.fromstring(b.encode("utf-8"))
        except Exception:
            return -1, []
        for p in root.findall("position"):
            g = lambda t: (p.findtext(t) or "").strip()
            desc = "\n".join((d.findtext("name") or "") + "\n" + strip_html(d.findtext("value") or "") for d in p.findall(".//jobDescription"))
            locs = [g("office")] + [o.text or "" for o in p.findall(".//additionalOffices/office")]
            jobs.append(dict(id=g("id"), title=g("name"), url=f"https://{slug}.jobs.personio.{dom}/job/{g('id')}", locs=[l for l in locs if l],
                             wp="", posted=g("createdAt")[:10], etype=g("employmentType") + " " + g("schedule"), comp="", desc=desc))
        return 200, jobs
    if provider == "teamtailor":
        st, b = get(f"https://{slug}.teamtailor.com/jobs.rss", tries=2)
        if st != 200:
            return st, []
        try:
            root = ET.fromstring(b.encode("utf-8"))
        except Exception:
            return -1, []
        ns = {"tt": "https://teamtailor.com/locations"}
        for it in root.iter("item"):
            locs = [" ".join((x.text or "") for x in l) for l in it.findall(".//tt:location", ns)]
            jobs.append(dict(id=it.findtext("guid"), title=it.findtext("title"), url=it.findtext("link"), locs=[l.strip() for l in locs if l.strip()],
                             wp=it.findtext("remoteStatus") or "", posted=it.findtext("pubDate") or "", etype="", comp="",
                             desc=strip_html(it.findtext("description") or "")))
        return 200, jobs
    if provider == "smartrecruiters":
        out, off = [], 0
        while True:
            st, b = get(f"https://api.smartrecruiters.com/v1/companies/{quote(slug)}/postings?limit=100&offset={off}", tries=3)
            if st != 200:
                return (st, out) if not out else (200, out)
            d = json.loads(b)
            for j in d.get("content", []):
                lo = j.get("location") or {}
                locs = [", ".join(x for x in [lo.get("city"), lo.get("region"), lo.get("country")] if x)]
                if lo.get("remote"):
                    locs.append("Remote")
                out.append(dict(id=j.get("id"), title=j.get("name"), url=f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}", locs=locs,
                                wp="Remote" if lo.get("remote") else ("Hybrid" if lo.get("hybrid") else ""), posted=(j.get("releasedDate") or "")[:10],
                                etype=(j.get("typeOfEmployment") or {}).get("label", ""), comp="", desc=None,
                                _detail=f"https://api.smartrecruiters.com/v1/companies/{quote(slug)}/postings/{j.get('id')}"))
            off += 100
            if off >= d.get("totalFound", 0) or off > 3000:
                return 200, out
    if provider == "rippling":
        st, b = get(f"https://ats.rippling.com/api/v2/board/{quote(slug)}/jobs", tries=3)
        if st != 200:
            return st, []
        for j in json.loads(b).get("items", []):
            locs = [l.get("name", "") for l in j.get("locations") or []]
            jobs.append(dict(id=j.get("id"), title=j.get("name"), url=j.get("url"), locs=locs,
                             wp=" ".join(l.get("workplaceType", "") or "" for l in j.get("locations") or []), posted="", etype="", comp="",
                             desc=None, _detail=f"https://ats.rippling.com/api/v2/board/{quote(slug)}/jobs/{j.get('id')}"))
        return 200, jobs
    if provider == "breezy":
        st, b = get(f"https://{slug}.breezy.hr/json", tries=2)
        if st != 200:
            return st, []
        try:
            arr = json.loads(b)
        except Exception:
            return -1, []
        for j in arr:
            lo = j.get("location") or {}
            locs = [lo.get("name") or "", (lo.get("country") or {}).get("name", "") if isinstance(lo.get("country"), dict) else ""]
            if lo.get("is_remote"):
                locs.append("Remote")
            jobs.append(dict(id=j.get("id"), title=j.get("name"), url=j.get("url"), locs=[l for l in locs if l], wp="Remote" if lo.get("is_remote") else "",
                             posted=(j.get("published_date") or "")[:10], etype=(j.get("type") or {}).get("name", "") if isinstance(j.get("type"), dict) else "",
                             comp=j.get("salary") or "", desc=None, _detail=j.get("url")))
        return 200, jobs
    if provider == "pinpoint":
        st, b = get(f"https://{slug}.pinpointhq.com/postings.json", tries=2)
        if st != 200:
            return st, []
        for j in json.loads(b).get("data", []):
            jobs.append(dict(id=j.get("id"), title=j.get("title"), url=j.get("url"), locs=[(j.get("location") or {}).get("name", "")],
                             wp=j.get("workplace_type") or "", posted="", etype=j.get("employment_type") or "", comp=(j.get("compensation") or ""),
                             desc=strip_html((j.get("description") or "") + "\n" + (j.get("key_responsibilities") or "") + "\n" + (j.get("skills_knowledge_expertise") or ""))))
        return 200, jobs
    if provider == "workable":
        st, b = get(f"https://apply.workable.com/api/v1/widget/accounts/{quote(slug)}?details=true", tries=3)
        if st != 200:
            return st, []
        for j in json.loads(b).get("jobs", []):
            locs = [", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)]
            for l in j.get("locations") or []:
                locs.append(", ".join(x for x in [l.get("city"), l.get("region"), l.get("country")] if x))
            if j.get("telecommuting"):
                locs.append("Remote")
            jobs.append(dict(id=j.get("shortcode"), title=j.get("title"), url=j.get("url") or j.get("shortlink"), locs=[l for l in locs if l],
                             wp="Remote" if j.get("telecommuting") else "", posted=(j.get("published_on") or j.get("created_at") or "")[:10],
                             etype=j.get("employment_type") or "", comp="", desc=strip_html(j.get("description") or "")))
        return 200, jobs
    return -2, []


def detail(provider, j):
    u = j.pop("_detail", None)
    if not u:
        return j
    st, b = get(u, tries=2, headers={"Accept": "text/html,*/*"} if provider == "breezy" else None)
    if st != 200:
        j["desc"] = ""; j["detail_status"] = st
        return j
    if provider == "breezy":
        m = re.search(r'(?is)<div class="description[^"]*">(.*?)<div class="(apply|bottom|share)', b)
        j["desc"] = strip_html(m.group(1) if m else b)[:30000]
        return j
    try:
        d = json.loads(b)
    except Exception:
        j["desc"] = ""
        return j
    if provider == "smartrecruiters":
        secs = (d.get("jobAd") or {}).get("sections") or {}
        j["desc"] = strip_html("\n".join((v or {}).get("title", "") + "\n" + (v or {}).get("text", "") for v in secs.values()))
    elif provider == "rippling":
        desc = d.get("description") or {}
        j["desc"] = strip_html((desc.get("company") or "") + "\n" + (desc.get("role") or "") if isinstance(desc, dict) else str(desc))
        j["etype"] = (d.get("employmentType") or {}).get("label", "") if isinstance(d.get("employmentType"), dict) else str(d.get("employmentType") or "")
        j["comp"] = json.dumps(d.get("payRangeDetails") or "")[:300]
    return j


def label_class(R, locs, wp):
    """Location label only (no body): home / region / eu / non_eu / remote / blank / other."""
    L = " | ".join(locs or [])
    remote = bool(REMOTE.search(L)) or (wp or "").strip().lower() == "remote"
    if R.HOME.search(L):
        return "home"
    eu = any(R.IN_REGION.search(l) for l in locs or [])
    non = any((R.OUTSIDE.search(l) or US_STATES.search(l)) and not R.IN_REGION.search(l) for l in locs or [])
    if R.REGION.search(L):
        return "region"
    if eu and non:
        return "mixed_remote" if remote else "mixed"
    if eu:
        return "eu_remote" if remote else "eu_place"
    if non:
        return "non_eu_remote" if remote else "non_eu"
    if remote:
        return "remote"
    return "blank" if not L.strip() else "other"


def board_path(R, provider, slug):
    return R.boards_dir / f"{provider}__{re.sub(r'[^A-Za-z0-9._-]', '_', slug)}.json.gz"


def process_board(R, b, refresh=False):
    provider, slug = b["provider"], b["slug"]
    fp = board_path(R, provider, slug)
    if fp.exists() and not refresh:
        try:
            return json.loads(gzip.decompress(fp.read_bytes()))
        except Exception:
            pass
    try:
        st, jobs = board_fetch(provider, slug)
    except Exception as e:
        st, jobs = -3, []
        R.log("ERR", provider, slug, type(e).__name__, str(e)[:120])
    rows, n_detail = [], 0
    for j in jobs:
        t = j.get("title") or ""
        if not R.KEEP.search(t) or R.NEVER.search(t):
            continue
        lab = label_class(R, j.get("locs") or [], j.get("wp"))
        if j.get("desc") is None:
            # Per-posting detail call: skip only labels that are plainly outside Europe and not remote.
            if lab == "non_eu" and not R.SKILL.search(t):
                j.pop("_detail", None)
                rows.append({**{k: v for k, v in j.items() if k != "desc"}, "label": lab, "skill": None, "body": "skipped_non_eu"})
                continue
            j = detail(provider, j); n_detail += 1
        desc = j.pop("desc", "") or ""
        j.pop("_detail", None)
        skill = bool(R.SKILL.search(t) or R.SKILL.search(desc))
        rec = dict(j, label=lab, skill=skill, desc_len=len(desc))
        if skill:
            rec["desc"] = desc[:24000]
        rows.append(rec)
    res = dict(provider=provider, slug=slug, status=st, n_jobs=len(jobs), n_detail=n_detail, rows=rows,
               fetched_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    if st not in (0, -3, 429, 500, 502, 503, 504):  # transient failures stay uncached so a rerun retries them
        fp.write_bytes(gzip.compress(json.dumps(res).encode()))
    return res


CONC = {"ashby": 6, "greenhouse": 8, "greenhouse_eu": 3, "lever": 5, "lever_eu": 3, "recruitee": 5, "personio": 5, "teamtailor": 5,
        "smartrecruiters": 5, "rippling": 3, "breezy": 3, "pinpoint": 3, "workable": 2}


def cmd_fetch(R, args):
    boards = json.loads(Path(args.boards).read_text() if args.boards else (R.dir / "boards2.json").read_text())
    if args.providers:
        boards = [b for b in boards if b["provider"] in args.providers.split(",")]
    if args.skip_status:
        # reuse an earlier status file to skip boards that returned 404/410 (dead slugs)
        dead = {(s["provider"], s["slug"].lower()) for s in json.loads(Path(args.skip_status).read_text()) if s.get("status") in (404, 410)}
        n0 = len(boards)
        boards = [b for b in boards if (b["provider"], b["slug"].lower()) not in dead]
        R.log("skipping known-dead boards:", n0 - len(boards))
    if args.limit:
        boards = boards[:args.limit]
    per = defaultdict(list)
    for b in boards:
        per[b["provider"]].append(b)
    done, stats = Counter(), Counter()

    def run_provider(p, lst):
        with ThreadPoolExecutor(CONC.get(p, 3)) as ex:
            for f in as_completed([ex.submit(process_board, R, b, args.refresh) for b in lst]):
                r = f.result()
                with lock:
                    done[p] += 1; stats[(p, r["status"])] += 1
                    if done[p] % 250 == 0:
                        R.log("progress", p, done[p], "/", len(lst))
    threads = [threading.Thread(target=run_provider, args=(p, l)) for p, l in per.items()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    R.log("FETCH DONE", {f"{p}:{s}": n for (p, s), n in sorted(stats.items())})


# ---------------------------------------------------------------- triage (offline)
def sentences(desc, pat, n=3):
    out = []
    for m in pat.finditer(desc):
        a = max(desc.rfind(".", 0, m.start()), desc.rfind("\n", 0, m.start())) + 1
        e = [x for x in (desc.find(".", m.end()), desc.find("\n", m.end())) if x != -1]
        s = desc[a:(min(e) + 1 if e else len(desc))].strip()
        if 6 < len(s) and s[:300] not in out:
            out.append(s[:300])
        if len(out) >= n:
            break
    return out


def geo(R, j):
    """(scope, evidence quotes). Body evidence overrides a city-only label; an explicit restriction overrides 'remote'."""
    desc, lab = j.get("desc") or "", j.get("label")
    head = desc[:1200] + "\n" + desc[-2500:]  # hiring-region statements sit in the intro or the closing section
    us = sentences(desc, US_ONLY)
    elsewhere = sentences(desc, ELSEWHERE_ONLY)
    onsite = sentences(desc, ONSITE)
    region = sentences(desc, R.REGION_REMOTE)
    home_body = [s for s in sentences(desc, R.HOME, 4) if not re.search(r"offices? in|hubs? in|locations?:|teams? in", s, re.I) or REMOTE.search(s)]
    remote_body = bool(re.search(r"fully remote|100% remote|remote[- ]first|remote position|remote role|work(ing)? remotely|fully distributed|"
                                 r"work from anywhere|remote \(", desc, re.I)) or bool(REMOTE.search(head))
    if lab == "home":
        return "home_listed", onsite[:1]
    if home_body and (remote_body or lab in ("region", "remote", "eu_remote", "mixed_remote", "blank")):
        return "home_in_body", home_body[:2]
    if lab == "region":
        return ("region_restricted", elsewhere) if elsewhere else ("region", region[:1])
    if lab in ("non_eu", "non_eu_remote"):
        if region and not us:
            return "region_in_body", region[:2]
        return "elsewhere", us[:1] or [f"label {' | '.join(j.get('locs') or [])[:80]}"]
    if lab in ("eu_remote", "mixed_remote"):
        if region:
            return "countries+region_body", region[:2]
        return "countries_only", [" | ".join(j.get("locs") or [])[:160]] + elsewhere[:1]
    if lab in ("eu_place", "mixed"):
        if region and remote_body and not onsite:
            return "place+region_body", region[:2]
        if remote_body and not onsite:
            return "countries_only", [" | ".join(j.get("locs") or [])[:160]]
        return "onsite_or_place", onsite[:1] or [" | ".join(j.get("locs") or [])[:120]]
    # remote / blank / other labels: decide from the body
    if region and not (us and not R.REGION.search(" ".join(region))):
        return "region_in_body", region[:2]
    if us:
        return "elsewhere", us[:2]
    if elsewhere:
        return "elsewhere", elsewhere[:2]
    if lab == "other" and not remote_body:
        return "onsite_or_place", [" | ".join(j.get("locs") or [])[:120]]
    return "remote_unknown", []


KEEP_SCOPES = ("home_listed", "home_in_body", "region", "region_in_body", "countries+region_body", "place+region_body", "remote_unknown")
SCOPE_RANK = {"home_listed": 6, "home_in_body": 6, "region": 4, "region_in_body": 4, "countries+region_body": 3,
              "place+region_body": 3, "remote_unknown": 1}


def req_section(desc, n=900):
    m = SECTION.search(desc)
    best = None
    for m in SECTION.finditer(desc):
        if re.search(r"require|qualif|bring|need|you have|about you|must|who you are|profile|looking for|skills", m.group(0), re.I):
            best = m
            break
    return desc[best.end():best.end() + n].strip() if best else ""


# Query parameters that identify a posting (e.g. careers.example.com/?gh_jid=123). Every other
# parameter (utm_*, source, ...) is dropped so tracking variants of one URL still match.
JOB_QUERY_KEYS = re.compile(r"(?i)^(gh_jid|jid|job_?id|jobid|id|posting_?id|position_?id|vacancy_?id|req(uisition)?_?id)$")


def norm_url(u):
    """Canonical form for exact-requisition dedup: no fragment or tracking query, but a job-id query
    parameter is kept, so two postings on one careers page with only ?gh_jid= differing stay distinct."""
    base, _, query = u.split("#")[0].partition("?")
    keep = sorted(kv.rstrip("/.,;") for kv in query.split("&") if "=" in kv and JOB_QUERY_KEYS.match(kv.split("=", 1)[0]))
    return (base.rstrip("/.,;") + ("?" + "&".join(keep) if keep else "")).lower()


def cmd_triage(R, args):
    dedup = set()
    ids = set()
    for f in args.dedup or []:
        for l in Path(f).read_text(errors="replace").splitlines():
            for u in re.findall(r"https?://[^\s|)\]>\"']+", l):
                u = norm_url(u)
                dedup.add(u)
                for m in re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|(?<![0-9])[0-9]{6,12}(?![0-9])", u):
                    ids.add(m)
    excl = []
    for f in args.exclude or []:
        excl += [l.split("|")[0].strip().lower() for l in Path(f).read_text().splitlines() if l.strip() and not l.startswith("#")]
    excl_norm = [re.sub(r"[^a-z0-9]", "", e.split("(")[0]) for e in excl]
    excl_norm = [e for e in excl_norm if len(e) > 3]
    norm = lambda v: re.sub(r"[^a-z0-9]", "", v.lower())
    seen = defaultdict(set)  # normalized title -> normalized company names already judged by hand
    for f in args.seen or []:
        for l in Path(f).read_text(errors="replace").splitlines():
            parts = [x.strip() for x in l.split("|")]
            if len(parts) >= 3 and not l.startswith("#"):
                seen[norm(parts[1])].add(norm(re.sub(r"\(.*?\)", "", parts[0])))
                for alias in re.findall(r"\(([^)]+)\)", parts[0]):
                    seen[norm(parts[1])].add(norm(alias))
    seen_companies = {c for v in seen.values() for c in v if len(c) > 3}
    drops = open(R.dir / "drops.jsonl", "w")
    funnel = Counter()
    kept = []

    def drop(j, stage, reason, quote=""):
        funnel[f"drop:{stage}"] += 1
        drops.write(json.dumps(dict(slug=j["slug"], title=j.get("title"), url=j.get("url"), locs=j.get("locs"), stage=stage,
                                    reason=reason, quote=quote[:240])) + "\n")

    for fp in sorted(R.boards_dir.glob("*.json.gz")):
        try:
            r = json.loads(gzip.decompress(fp.read_bytes()))
        except Exception:
            continue
        funnel["boards"] += 1
        funnel[f"board_status:{r['status']}"] += 1
        funnel["postings"] += r.get("n_jobs", 0)
        for j in r["rows"]:
            j["provider"], j["slug"] = r["provider"], r["slug"]
            t = (j.get("title") or "").strip()
            funnel["engineering_titles"] += 1
            if j.get("body") == "skipped_non_eu":
                funnel["drop:label_non_eu_no_body"] += 1
                continue
            if not j.get("skill"):
                funnel["drop:no_skill_in_title_or_body"] += 1
                continue
            funnel["skill_rows"] += 1
            desc = j.get("desc") or ""
            skill_title = bool(R.SKILL.search(t))
            m = R.OUT.search(t)
            if m:
                drop(j, "title_scope", m.group(0)); continue
            m = R.OUT_UNLESS.search(t)
            if m and not skill_title:
                drop(j, "title_scope", m.group(0)); continue
            m = R.LEVEL.search(t)
            if m:
                drop(j, "level", m.group(0)); continue
            scope, ev = geo(R, j)
            if scope not in KEEP_SCOPES:
                # countries_only is a labelled bucket, not a silent drop
                drop(j, "geo:" + scope, scope, " // ".join(ev));
                if scope != "countries_only":
                    continue
            flags = []
            n_skill = len(R.SKILL.findall(desc)) + (3 if skill_title else 0)
            langs = Counter(x.lower() for x in R.OTHER.findall(desc))
            top = langs.most_common(1)
            if top and top[0][1] > n_skill:
                flags.append(f"other-lang {top[0][0]}:{top[0][1]} vs skill:{n_skill}")
            if n_skill <= 1 and not skill_title:
                flags.append("skill-mentioned-once")
            b2b = sentences(desc, B2B, 2)
            emp = sentences(desc, EMPLOYEE, 2)
            if b2b or re.search(r"contract|freelanc", j.get("etype") or "", re.I):
                flags.append("b2b-wording")
            if emp:
                flags.append("employee-wording")
            if ONCALL.search(desc):
                flags.append("on-call-mention")
            if LEAD_REQ.search(desc):
                flags.append("lead-required?")
            if LLM_REQ.search(desc):
                flags.append("llm-experience?")
            nfe = len(FRONTEND.findall(desc))
            if nfe >= 4:
                flags.append(f"frontend:{nfe}")
            if sentences(desc, ONSITE, 1) and scope != "home_listed":
                flags.append("onsite/hybrid-wording")
            u = norm_url(j.get("url") or "")
            jid = str(j.get("id") or "")
            co = re.sub(r"[^a-z0-9]", "", j["slug"].lower())
            if u in dedup or (len(jid) >= 6 and jid in ids):
                dd = "known_req"
            elif any(e in co or co in e for e in excl_norm if len(co) > 3):
                dd = "applied_company?"
            elif any(c and len(c) > 2 and (c in co or co in c) for c in seen.get(norm(t), ())):
                dd = "seen_before"
            else:
                dd = "new"
            if dd == "new" and len(co) > 3 and any(c == co or (len(c) > 5 and (c in co or co in c)) for c in seen_companies):
                flags.append("company-seen-before")
            score = SCOPE_RANK.get(scope, 0) + (2 if skill_title else 0) + (2 if SENIOR.search(t) else 0)
            score += (3 if "b2b-wording" in flags else 0) + (1 if re.search(r"back-?\s?end|python|\bapi|integration|platform", t, re.I) else 0)
            score -= sum(2 for f in flags if f.startswith(("other-lang", "frontend", "llm", "lead", "onsite")))
            score -= 1 if "skill-mentioned-once" in flags else 0
            score += 1 if (j.get("posted") or "") >= time.strftime("%Y-%m-%d", time.gmtime(time.time() - 45 * 86400)) else 0
            kept.append(dict(provider=j["provider"], slug=j["slug"], title=t, url=j.get("url"), id=j.get("id"), locs=j.get("locs"), wp=j.get("wp"),
                             posted=j.get("posted"), etype=j.get("etype"), comp=j.get("comp"), scope=scope, geo_evidence=ev, flags=flags,
                             b2b=b2b, employee=emp, pay=[m.group(0)[:70] for m in PAY.finditer(desc)][:2], dedup=dd, score=score,
                             bucket="country_unconfirmed" if scope == "countries_only" else "main", requirements=req_section(desc)))
    drops.close()
    groups = defaultdict(list)
    for x in kept:
        groups[(x["slug"].lower(), re.sub(r"\W+", " ", x["title"].lower()).strip())].append(x)
    short = []
    for xs in groups.values():
        best = dict(max(xs, key=lambda y: y["score"]))
        best["all_locs"] = sorted({l for y in xs for l in (y["locs"] or [])})[:14]
        best["urls"] = [y["url"] for y in xs][:6]
        best["bucket"] = "main" if any(y["bucket"] == "main" for y in xs) else "country_unconfirmed"
        best["dedup"] = "known_req" if any(y["dedup"] == "known_req" for y in xs) else best["dedup"]
        short.append(best)
    short.sort(key=lambda y: (y["bucket"] != "main", -y["score"]))
    funnel["kept_rows"] = len(kept)
    funnel["groups_main"] = sum(1 for y in short if y["bucket"] == "main")
    funnel["groups_country_unconfirmed"] = sum(1 for y in short if y["bucket"] != "main")
    for k, v in Counter(y["scope"] for y in short if y["bucket"] == "main").items():
        funnel[f"main_scope:{k}"] = v
    for k, v in Counter(y["dedup"] for y in short if y["bucket"] == "main").items():
        funnel[f"main_dedup:{k}"] = v
    (R.dir / "shortlist2.json").write_text(json.dumps(short))
    (R.dir / "funnel.json").write_text(json.dumps(dict(sorted(funnel.items())), indent=1))
    with open(R.dir / "shortlist2.md", "w") as fh:
        for y in short:
            fh.write(f"{y['score']:>3} | {y['bucket'][:7]} | {y['slug']} | {y['title'][:80]} | {y['scope']} | {'; '.join(y['all_locs'])[:90]} | "
                     f"{y['posted']} | {(y['etype'] or '')[:18]} | {','.join(y['flags'])} | {y['dedup']} | {y['url']}\n")
    R.log("TRIAGE", json.dumps(dict(sorted(funnel.items()))))


def cmd_digest(R, args):
    """Compact reading list from shortlist2.json: one block per role group with the quotes that decide the gates."""
    rows = json.loads((R.dir / "shortlist2.json").read_text())
    want_dedup = set(args.dedup.split(",")) if args.dedup else None
    want_scope = set(args.scope.split(",")) if args.scope else None
    skip = args.skip_flag.split(",") if args.skip_flag else []
    need = args.need_flag.split(",") if args.need_flag else []
    sel = [y for y in rows if y["bucket"] == args.bucket and (not want_dedup or y["dedup"] in want_dedup)
           and (not want_scope or y["scope"] in want_scope) and y["score"] >= args.min_score
           and not any(f.startswith(tuple(skip)) for f in y["flags"]) and all(any(f.startswith(n) for f in y["flags"]) for n in need)
           and (not args.title or re.search(args.title, y["title"], re.I))]
    print(f"# {len(sel)} groups match; showing {args.offset}..{args.offset + args.count}")
    for y in sel[args.offset:args.offset + args.count]:
        print(f"\n## [{y['score']}] {y['slug']} | {y['title']} | {y['scope']} | {'; '.join(y['all_locs'])[:110]} | wp={y.get('wp')} | {y['posted']} | {y.get('etype')} | {y.get('comp') or ''}")
        print(f"   {y['url']}  ({y['dedup']})  flags: {', '.join(y['flags'])}")
        for k in ("geo_evidence", "b2b", "employee", "pay"):
            if y.get(k):
                print(f"   {k}: " + " // ".join(str(v)[:220] for v in y[k][:2]))
        if args.req_chars and y.get("requirements"):
            print("   req: " + re.sub(r"\s+", " ", y["requirements"])[:args.req_chars])


def cmd_funnel(R, args):
    print((R.dir / "funnel.json").read_text())


def cmd_show(R, args):
    """Print the body passages that decide the gates for matching rows (slug::title substring match)."""
    keys = [k.lower() for k in args.keys]
    shown = {}  # (slug, title, body) -> index, so location twins of one posting print once
    for fp in sorted(R.boards_dir.glob("*.json.gz")):
        if not any(k.split("::")[0] in fp.name.lower() for k in keys):
            continue
        r = json.loads(gzip.decompress(fp.read_bytes()))
        for j in r["rows"]:
            tag = f"{r['slug']}::{j.get('title')}".lower()
            if not any(all(p in tag for p in k.split("::")) for k in keys) or not j.get("desc"):
                continue
            j["slug"] = r["slug"]
            twin = (r["slug"], (j.get("title") or "").strip(), hash(j["desc"]))
            if twin in shown:
                print(f"   (same body also listed for {j.get('locs')}: {j.get('url')})")
                continue
            shown[twin] = 1
            print("=" * 100)
            print(f"{r['provider']} {r['slug']} | {j.get('title')} | {j.get('locs')} | wp={j.get('wp')} | {j.get('posted')} | {j.get('etype')} | {j.get('comp')}")
            print(j.get("url"))
            print(j["desc"][:args.chars] if args.full else "\n".join(
                f"  [{n}] {s}" for n, p in (("geo", R.REGION_REMOTE), ("home", R.HOME), ("us", US_ONLY), ("else", ELSEWHERE_ONLY), ("site", ONSITE),
                                           ("b2b", B2B), ("emp", EMPLOYEE), ("call", ONCALL), ("lead", LEAD_REQ), ("llm", LLM_REQ))
                for s in sentences(j["desc"], p, 3)) + "\n  [req] " + req_section(j["desc"], args.chars))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("enumerate", "fetch", "triage", "show", "funnel", "digest"):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True, help="run folder (cache, board list and outputs live here)")
        if name == "enumerate":
            p.add_argument("--crawls"); p.add_argument("--providers")
            p.add_argument("--seed", action="append", help="JSON list of {provider, slug} or any text file with ATS URLs")
            p.add_argument("--scan", action="append", help="folder of local evidence to harvest ATS slugs from")
        if name == "fetch":
            p.add_argument("--providers"); p.add_argument("--refresh", action="store_true"); p.add_argument("--limit", type=int)
            p.add_argument("--boards", help="board list to fetch instead of boards2.json (JSON list of {provider, slug})")
            p.add_argument("--skip-status", help="earlier board-status.json; boards that were 404/410 there are skipped")
        if name == "triage":
            p.add_argument("--dedup", action="append", help="file with known requisition URLs (any text; URLs are extracted)")
            p.add_argument("--exclude", action="append", help="file with company-level exclusions, one 'company | reason' per line")
            p.add_argument("--seen", action="append", help="'company | role | reason' lines already judged by hand (marked seen_before)")
        if name == "digest":
            p.add_argument("--bucket", default="main"); p.add_argument("--dedup"); p.add_argument("--scope"); p.add_argument("--title")
            p.add_argument("--min-score", type=int, default=-99); p.add_argument("--skip-flag"); p.add_argument("--need-flag")
            p.add_argument("--offset", type=int, default=0); p.add_argument("--count", type=int, default=40)
            p.add_argument("--req-chars", type=int, default=450)
        if name == "show":
            p.add_argument("keys", nargs="+"); p.add_argument("--full", action="store_true"); p.add_argument("--chars", type=int, default=1400)
    args = ap.parse_args()
    R = Run(args.run)
    {"enumerate": cmd_enumerate, "fetch": cmd_fetch, "triage": cmd_triage, "show": cmd_show, "funnel": cmd_funnel, "digest": cmd_digest}[args.cmd](R, args)


if __name__ == "__main__":
    main()
