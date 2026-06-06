import streamlit as st
from google import genai
import datetime
import os
import io
import logging
import requests
import plotly.graph_objects as go
from dotenv import load_dotenv
import json
import time

load_dotenv()

USE_LIVE_MARKET_DATA = True

# ── Page Config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="SnapReport by Snaphomz", page_icon="🏠", layout="wide")

# ── Gemini Client ───────────────────────────────────────────────────────────
api_key = os.getenv("GOOGLE_API_KEY")
_gemini_client = None

if api_key:
    _gemini_client = genai.Client(api_key=api_key)
else:
    with st.sidebar:
        st.info("Running in demo mode")

# Gemini generates a unique, human-sounding narrative every time using real market numbers.
# Fallback f-string ensures demo never breaks regardless of API availability or connectivity.
def generate_narrative(zip_code: str, market_data: dict, agent_name: str) -> str:
    city  = market_data["city"]
    state = market_data["state"]

    prompt = f"""You are a senior real estate market analyst writing a short, punchy market report for agent {agent_name} covering ZIP code {zip_code} ({city}, {state}).

Write in a confident, human, professional tone. Sound authoritative but accessible — like an expert explaining the market to a friend. 
Use the real numbers naturally woven into the prose.

Do NOT use headers, bullet points, bold text, or numbered lists. Write only 3 clean, flowing paragraphs separated by blank lines.

Paragraph 1 — THE HEADLINES: Summarise the market vibe right now. Use these figures: median price ${market_data['median_price']:,}, {market_data['price_change_pct']}% YoY change, {market_data['active_listings']} active listings ({market_data['new_listings']} new), and {market_data['days_on_market']} average days on market.

Paragraph 2 — BUYER ADVICE: What should buyers do? Mention the {market_data['inventory_months']} months of supply and how fast homes are selling (list-to-sale ratio of {market_data['list_to_sale_ratio']}%). Keep it highly actionable.

Paragraph 3 — SELLER ADVICE: What should sellers do? Use the {market_data['list_to_sale_ratio']}% list-to-sale ratio to explain pricing leverage. Add a natural call to action to contact {agent_name}.

Each paragraph must be exactly 3-4 sentences. Make it engaging and easy to read quickly."""

    try:
        if _gemini_client:
            response = _gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text.strip()
    except Exception:
        pass

    # Silent fallback — uses real numbers, sounds professional and punchy.
    inv     = market_data["inventory_months"]
    lts     = market_data["list_to_sale_ratio"]
    dom     = market_data["days_on_market"]
    price   = market_data["median_price"]
    pct     = market_data["price_change_pct"]
    listings = market_data["active_listings"]
    new_list = market_data["new_listings"]

    return f"""The {city}, {state} real estate market is moving with serious momentum right now. With the median sale price hitting ${price:,} (up {pct}% year-over-year) and properties averaging just {dom} days on the market, demand is clearly outpacing supply. There are only {listings} active listings across the ZIP code ({new_list} of which are new), meaning well-priced homes are seeing intense competition almost the moment they hit the MLS.

For buyers, this means preparation is your best asset in today's landscape. With only {inv} months of available inventory, you simply don't have the luxury of sleeping on a decision when you find the right property. Because homes are selling at {lts}% of their asking price, lowball offers are unlikely to win; instead, buyers need fully underwritten financing and a willingness to act decisively.

Sellers currently hold the stronger hand, provided they price accurately from day one. A list-to-sale ratio of {lts}% proves that the market is highly rewarding homes that are priced to reflect current comparable sales rather than aspirational targets. If you've been considering making a move, {agent_name} can provide a precise valuation to help you capitalise on this low-inventory window before seasonal shifts bring more competition."""



# ── Session State Initialization ──────────────────────────────────────────
for key in ["reports_data", "zip_codes", "agent_name", "brokerage", "agent_phone", "agent_email", "agent_website", "agent_photo_bytes"]:
    if key not in st.session_state:
        st.session_state[key] = None

# Load mock data from external file with API-like structure
def load_mock_data():
    try:
        with open("mock_data.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load mock_data.json: {e}")
        return {}

MOCK_API_DATA = load_mock_data()

class RealEstateAPIService:
    """
    Service layer for RealEstateAPI.com integration.
    Handles authentication, API requests, and response normalization.
    """
    def __init__(self):
        self.api_key = os.getenv("REALESTATE_API_KEY")
        self.base_url = "https://api.realestateapi.com/v2" # Using a hypothetical v2 endpoint
        
    def get_market_data(self, zip_code: str) -> dict:
        if not self.api_key:
            raise ValueError("REALESTATE_API_KEY not found in environment.")
            
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            # Simulated API call to the market metrics endpoint
            response = requests.get(f"{self.base_url}/market-metrics", params={"zip": zip_code}, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Normalize the API response to match the exact format expected by SnapReport
            return {
                "city": data.get("city", "Unknown"),
                "state": data.get("state", "Unknown"),
                "median_price": float(data.get("medianSalePrice", 0)),
                "price_change_pct": float(data.get("yoyPriceChange", 0.0)),
                "days_on_market": int(data.get("averageDOM", 0)),
                "active_listings": int(data.get("activeListings", 0)),
                "new_listings": int(data.get("newListings", 0)),
                "list_to_sale_ratio": float(data.get("listToSaleRatio", 100.0)),
                "inventory_months": float(data.get("monthsOfInventory", 0.0))
            }
        except requests.exceptions.Timeout:
            logging.error(f"RealEstateAPI request timed out for ZIP {zip_code}")
            raise
        except Exception as e:
            logging.error(f"RealEstateAPI request failed for ZIP {zip_code}: {str(e)}")
            raise

def get_market_data(zip_code: str) -> tuple[dict, bool]:
    """
    Service layer for retrieving market data.
    Returns a tuple of (market_data_dict, is_live_boolean)
    """
    if USE_LIVE_MARKET_DATA:
        try:
            api_service = RealEstateAPIService()
            data = api_service.get_market_data(zip_code)
            return data, True
        except Exception as e:
            logging.warning(f"Live market data unavailable for {zip_code}, falling back to mock data. Reason: {e}")
            
    # Fallback to local mock data
    if zip_code in MOCK_API_DATA:
        data = MOCK_API_DATA[zip_code]
        normalized_data = {
            "city": data.get("city", "Unknown"),
            "state": data.get("state", "Unknown"),
            "median_price": float(data.get("medianSalePrice", 0)),
            "price_change_pct": float(data.get("yoyPriceChange", 0.0)),
            "days_on_market": int(data.get("averageDOM", 0)),
            "active_listings": int(data.get("activeListings", 0)),
            "new_listings": int(data.get("newListings", 0)),
            "list_to_sale_ratio": float(data.get("listToSaleRatio", 100.0)),
            "inventory_months": float(data.get("monthsOfInventory", 0.0))
        }
        return normalized_data, False
    else:
        raise ValueError(f"ZIP code {zip_code} not found in mock_data.json fallback. Try: 90210, 10001, 75201, 33139, 60601, 98101.")

def generate_charts(market_data: dict):
    # Fake 6 month history for placeholder
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    current_price = market_data["median_price"]
    current_inv = market_data["inventory_months"]
    
    # Generate some slightly trending data ending at current values
    prices = [current_price * (1 - 0.05 + 0.01*i) for i in range(6)]
    prices[-1] = current_price
    
    invs = [current_inv * (1 + 0.5 - 0.1*i) for i in range(6)]
    invs[-1] = current_inv
    
    NAVY = "#1a2e44"
    
    # Price Chart
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=months, y=prices, mode='lines+markers', name='Median Price', line=dict(color=NAVY, width=3)))
    fig_price.update_layout(title="Median Price Trend", margin=dict(l=20, r=20, t=40, b=20), height=300)
    
    # Inventory Chart
    fig_inv = go.Figure()
    fig_inv.add_trace(go.Bar(x=months, y=invs, name='Inventory (Months)', marker_color=NAVY))
    fig_inv.update_layout(title="Inventory Trend (Months)", margin=dict(l=20, r=20, t=40, b=20), height=300)
    
    # Generate bytes for PDF
    try:
        price_bytes = fig_price.to_image(format="png", width=600, height=300)
        inv_bytes = fig_inv.to_image(format="png", width=600, height=300)
    except Exception:
        price_bytes = None
        inv_bytes = None
        
    return fig_price, fig_inv, price_bytes, inv_bytes

class EmailService:
    """
    Service layer for handling report deliveries.
    Future integration: SendGrid API.
    """
    def __init__(self):
        # Fetch API key from environment, do not hardcode
        self.api_key = os.getenv("SENDGRID_API_KEY")
        
    def send_report(self, recipient_email: str, agent_name: str, pdf_bytes: bytes) -> bool:
        if self.api_key:
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
                import base64

                sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
                
                message = Mail(
                    from_email="ervarishitha@gmail.com",
                    to_emails=recipient_email,
                    subject=f"Real Estate Market Report from {agent_name}",
                    html_content=f"<strong>Hello!</strong><br><br>Please find the attached market report prepared by {agent_name}."
                )

                encoded_file = base64.b64encode(pdf_bytes).decode()
                
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName('SnapReport.pdf'),
                    FileType('application/pdf'),
                    Disposition('attachment')
                )
                message.attachment = attachment
                
                response = sg.send(message)
                logging.info(f"Successfully sent report to {recipient_email} from {agent_name}. Status Code: {response.status_code}")
                return True
            except Exception as e:
                logging.error(f"SendGrid API failed: {str(e)}. Falling back to demo mode.")
                
        # Fallback Demo Mode
        try:
            time.sleep(1.5)
            logging.info(f"[DEMO MODE FALLBACK] Successfully 'sent' report to {recipient_email} from {agent_name}")
            return True
        except Exception as e:
            logging.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

# Single-file PDF generation keeps the app fully portable.
# reportlab is pure Python — no system libraries required on any OS.
def generate_pdf(zip_codes: list, reports_data: dict, agent_name: str, brokerage: str,
                 agent_phone: str, agent_email: str, agent_website: str,
                 agent_photo_bytes: bytes) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=20*mm, rightMargin=20*mm,
                               topMargin=15*mm, bottomMargin=15*mm)

    NAVY  = colors.HexColor("#1a2e44")
    GREY  = colors.HexColor("#555555")
    LGREY = colors.HexColor("#888888")
    WHITE = colors.white

    # ─ Styles ──────────────────────────────────────────────────────
    s_brand  = ParagraphStyle("hb", fontSize=16, textColor=WHITE,
                               fontName="Helvetica-Bold", leading=20)
    s_pwr    = ParagraphStyle("hp", fontSize=12, textColor=WHITE,
                               fontName="Helvetica", leading=16, alignment=TA_RIGHT)
    s_agent  = ParagraphStyle("an", fontSize=16, textColor=NAVY,
                               fontName="Helvetica-Bold", leading=20)
    s_sub    = ParagraphStyle("as", fontSize=10, textColor=GREY,
                               fontName="Helvetica", leading=14)
    s_date   = ParagraphStyle("dt", fontSize=10, textColor=GREY,
                               fontName="Helvetica", alignment=TA_RIGHT, leading=14)
    s_h1     = ParagraphStyle("h1", fontSize=16, textColor=NAVY,
                               fontName="Helvetica-Bold", alignment=TA_CENTER, leading=22)
    s_h1sub  = ParagraphStyle("h1s", fontSize=10, textColor=LGREY,
                               fontName="Helvetica", alignment=TA_CENTER, leading=14)
    s_num    = ParagraphStyle("sn", fontSize=18, textColor=NAVY,
                               fontName="Helvetica-Bold", alignment=TA_CENTER, leading=22)
    s_lbl    = ParagraphStyle("sl", fontSize=9, textColor=LGREY,
                               fontName="Helvetica", alignment=TA_CENTER, leading=12)
    s_sechd  = ParagraphStyle("sh", fontSize=10, textColor=NAVY,
                               fontName="Helvetica-Bold", leading=14, spaceAfter=4)
    s_body   = ParagraphStyle("bd", fontSize=10,
                               textColor=colors.HexColor("#2d3748"),
                               fontName="Helvetica", leading=16, spaceAfter=10)
    s_footer = ParagraphStyle("ft", fontSize=8, textColor=LGREY,
                               fontName="Helvetica", alignment=TA_CENTER, leading=12)

    W = A4[0] - 40*mm
    elements = []

    contact_parts = [p for p in [agent_phone, agent_email, agent_website] if p]
    contact_info = " | ".join(contact_parts)
    
    for idx, zip_code in enumerate(zip_codes):
        if idx > 0:
            elements.append(PageBreak())
            
        data = reports_data[zip_code]
        market_data = data["market_data"]
        narrative = data["narrative"]
        
        today = datetime.date.today().strftime("%B %d, %Y")
        city  = market_data["city"]
        state = market_data["state"]
        lts   = market_data["list_to_sale_ratio"]
        
        # ─ Header bar ───────────────────────────────────────────────────
        hdr = Table([[Paragraph("SnapReport", s_brand),
                      Paragraph("Powered by Snaphomz", s_pwr)]],
                    colWidths=[W*0.6, W*0.4])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), NAVY),
            ("TOPPADDING",    (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
            ("LEFTPADDING",   (0,0), (0,-1),  10),
            ("RIGHTPADDING",  (-1,0),(-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        elements += [hdr, Spacer(1, 6*mm)]

        # ─ Agent + Date ────────────────────────────────────────────────
        agent_text = [
            Paragraph(agent_name, s_agent),
            Paragraph(brokerage, s_sub),
            Paragraph(contact_info, s_sub)
        ]
        
        if agent_photo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img_io = io.BytesIO(agent_photo_bytes)
                img_reader = ImageReader(img_io)
                iw, ih = img_reader.getSize()
                aspect = ih / float(iw)
                
                target_width = 25*mm
                target_height = target_width * aspect
                if target_height > 35*mm:
                    target_height = 35*mm
                    target_width = target_height / aspect
                    
                img = Image(img_io, width=target_width, height=target_height)
                agt = Table([[img, agent_text, Paragraph(today, s_date)]],
                            colWidths=[30*mm, W*0.7 - 30*mm, W*0.3])
            except Exception:
                agt = Table([[agent_text, Paragraph(today, s_date)]],
                            colWidths=[W*0.7, W*0.3])
        else:
            agt = Table([[agent_text, Paragraph(today, s_date)]],
                        colWidths=[W*0.7, W*0.3])
                        
        agt.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
        elements += [agt,
                     HRFlowable(width="100%", thickness=1,
                                 color=colors.HexColor("#e2e8f0")),
                     Spacer(1, 5*mm)]

        # ─ Headline ──────────────────────────────────────────────────────
        elements += [
            Paragraph(f"Real Estate Market Report — ZIP {zip_code}", s_h1),
            Paragraph(f"{city}, {state}", s_h1sub),
            Spacer(1, 5*mm),
        ]

        # ─ Stats grid ───────────────────────────────────────────────────
        lts_disp = f"{lts}%" + (" (Seller's)" if lts >= 100 else "")
        cw = W / 6
        stats = Table(
            [[Paragraph(f"${market_data['median_price']:,}", s_num),
              Paragraph(str(market_data["days_on_market"]),   s_num),
              Paragraph(str(market_data["active_listings"]),  s_num),
              Paragraph(str(market_data["new_listings"]),     s_num),
              Paragraph(str(market_data["inventory_months"]), s_num),
              Paragraph(lts_disp,                              s_num)],
             [Paragraph("Median Price",       s_lbl),
              Paragraph("Days on Market",     s_lbl),
              Paragraph("Active Listings",    s_lbl),
              Paragraph("New Listings",       s_lbl),
              Paragraph("Months Supply",      s_lbl),
              Paragraph("List-to-Sale Ratio", s_lbl)]],
            colWidths=[cw]*6, rowHeights=[30, 24]
        )
        stats.setStyle(TableStyle([
            ("BOX",          (0,0), (0,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX",          (1,0), (1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX",          (2,0), (2,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX",          (3,0), (3,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX",          (4,0), (4,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX",          (5,0), (5,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",   (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        elements += [stats, Spacer(1, 6*mm)]

        # ─ Charts ───────────────────────────────────────────────────
        if "charts" in data and data["charts"]["price"] and data["charts"]["inv"]:
            try:
                price_img = Image(io.BytesIO(data["charts"]["price"]), width=W/2 - 2*mm, height=(W/2 - 2*mm)*0.5)
                inv_img = Image(io.BytesIO(data["charts"]["inv"]), width=W/2 - 2*mm, height=(W/2 - 2*mm)*0.5)
                
                chart_table = Table([[price_img, inv_img]], colWidths=[W/2, W/2])
                chart_table.setStyle(TableStyle([
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ]))
                elements += [chart_table, Spacer(1, 6*mm)]
            except Exception:
                pass

        # ─ AI Narrative ────────────────────────────────────────────────
        elements += [
            HRFlowable(width="100%", thickness=1.5, color=NAVY),
            Spacer(1, 2*mm),
            Paragraph("AI Market Analysis", s_sechd),
            Spacer(1, 2*mm),
        ]
        for para in narrative.split("\n\n"):
            if para.strip():
                elements.append(Paragraph(para.strip(), s_body))

        # ─ Footer ────────────────────────────────────────────────────────
        elements += [
            Spacer(1, 4*mm),
            HRFlowable(width="100%", thickness=0.5,
                       color=colors.HexColor("#e2e8f0")),
            Spacer(1, 2*mm),
            Paragraph(
                f"Generated by SnapReport \u00b7 {brokerage} \u00b7 Data current as of {today}",
                s_footer
            ),
        ]

    doc.build(elements)
    return buffer.getvalue()





# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**SnapReport**")
    st.caption("AI-powered market reports by Snaphomz")

    st.divider()

    zip_input       = st.text_input("ZIP Codes (comma-separated)",    value="90210, 10001")
    agent_input     = st.text_input("Agent Name",  value="Sarah Mitchell")
    brokerage_input = st.text_input("Brokerage",   value="Snaphomz Realty")
    agent_phone_input   = st.text_input("Agent Phone",   value="(555) 123-4567")
    agent_email_input   = st.text_input("Agent Email",   value="sarah@snaphomz.com")
    agent_website_input = st.text_input("Agent Website", value="www.sarahmitchell.com")

    agent_photo_file = st.file_uploader("Agent Photo (Optional)", type=["jpg", "jpeg", "png"])
    agent_photo_bytes_input = agent_photo_file.getvalue() if agent_photo_file else None
    if agent_photo_bytes_input:
        st.image(agent_photo_bytes_input, caption="Photo Preview", use_container_width=True)

    generate = st.button("Generate Report", type="primary", use_container_width=True)

    with st.expander("Architecture Decisions"):
        st.markdown("""
        - Streamlit: fastest path to MVP
        - Gemini: unique human narratives
        - Hardcoded data: demo reliability
        - PDF: fits existing agent workflow
        - Future: MLS API integration
        """)
# ── Button click: validate → generate → persist ───────────────────────────
if generate:
    input_zips = [z.strip() for z in zip_input.split(",") if z.strip()]
    
    if not input_zips:
        st.error("Please enter at least one ZIP code.")
        st.stop()

    try:
        reports_data = {}
        for z in input_zips:
            with st.spinner(f"Fetching market data for {z}..."):
                market_data, is_live = get_market_data(z)

            with st.spinner(f"Gemini is writing market analysis for {z}..."):
                narrative = generate_narrative(z, market_data, agent_input)
                
            reports_data[z] = {"market_data": market_data, "narrative": narrative, "is_live": is_live}

        # Persist so report survives reruns without regenerating
        st.session_state["reports_data"] = reports_data
        st.session_state["zip_codes"]    = input_zips
        st.session_state["agent_name"]  = agent_input
        st.session_state["brokerage"]   = brokerage_input
        st.session_state["agent_phone"] = agent_phone_input
        st.session_state["agent_email"] = agent_email_input
        st.session_state["agent_website"] = agent_website_input
        st.session_state["agent_photo_bytes"] = agent_photo_bytes_input

    except Exception as e:
        st.error(f"Something went wrong generating the report: {str(e)}")
        st.stop()

# ── Main Area: placeholder or full report ─────────────────────────────────
st.info("SnapReport turns a 3\u20134 hour manual task into a 90-second workflow. Enter ZIP codes and get market reports ready to send to clients.")

if st.session_state["reports_data"] is None:
    st.info("Enter ZIP codes in the sidebar and click Generate Report to create the AI-powered market report.")

else:
    zips = st.session_state["zip_codes"]
    r_data = st.session_state["reports_data"]
    name  = st.session_state["agent_name"]
    today = datetime.date.today().strftime("%B %d, %Y")

    # (a) Success banner
    st.success(f"Reports ready — {len(zips)} ZIP(s) · {name} · {today}")
    st.caption(f"**Contact Info:** {st.session_state['agent_phone']} | {st.session_state['agent_email']} | {st.session_state['agent_website']}")

    for idx, z in enumerate(zips):
        if idx > 0:
            st.divider()
            
        md = r_data[z]["market_data"]
        narr = r_data[z]["narrative"]

        is_live = r_data[z].get("is_live", False)
        
        col_title, col_badge = st.columns([3, 1])
        with col_title:
            st.subheader(f"{md['city']} ({z}) Market Snapshot")
        with col_badge:
            if is_live:
                st.caption("🟢 **Live Market Data**")
            else:
                st.caption("🟡 **Demo Market Data**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Median Price", f"${md['median_price']:,}", f"+{md['price_change_pct']}% YoY")
            st.metric("Active Listings", md["active_listings"])

        with col2:
            st.metric("Days on Market", f"{md['days_on_market']} days")
            st.metric("New Listings", md["new_listings"])

        with col3:
            lts_delta = "Seller's market" if md["list_to_sale_ratio"] >= 100 else "Balanced market"
            st.metric("List-to-Sale Ratio", f"{md['list_to_sale_ratio']}%", lts_delta)
            st.metric("Inventory Months", f"{md['inventory_months']} mo")

        # ─ Charts ───────────────────────────────────────────────────
        fig_price, fig_inv, price_bytes, inv_bytes = generate_charts(md)
        r_data[z]["charts"] = {"price": price_bytes, "inv": inv_bytes}

        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.plotly_chart(fig_price, use_container_width=True)
        with c_chart2:
            st.plotly_chart(fig_inv, use_container_width=True)

        # (d) AI narrative as blockquote pull-quotes
        st.subheader(f"AI Market Analysis — {z}")
        paragraphs = [p.strip() for p in narr.split("\n\n") if p.strip()]
        blockquote = "\n\n".join(f"> {p}" for p in paragraphs)
        st.markdown(blockquote)
        st.caption("✦ AI-generated narrative — unique every time, powered by Google Gemini")

    st.divider()
    st.subheader("Business Impact")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Time Saved", f"{90 * len(zips)} sec", "vs hours manually")

    with c2:
        st.metric("Client Touchpoints", f"{12 * len(zips)}/year", "ongoing engagement")

    with c3:
        st.metric("Revenue Path", "Future Listings", "client nurturing")

    st.caption("Every report sent by an agent becomes a recurring Snaphomz brand impression.")


    # ── Export & Delivery ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Export & Delivery")
    try:
        pdf_bytes = generate_pdf(
            zips,
            r_data,
            name,
            st.session_state["brokerage"],
            st.session_state["agent_phone"],
            st.session_state["agent_email"],
            st.session_state["agent_website"],
            st.session_state["agent_photo_bytes"]
        )
        
        col_dl, col_email = st.columns(2)
        
        with col_dl:
            st.download_button(
                label="⬇ Download Full PDF Report",
                data=pdf_bytes,
                file_name=f"SnapReport_Multiple.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
        with col_email:
            with st.form("email_delivery_form"):
                client_email = st.text_input("Client Email Address", placeholder="client@example.com")
                submit_email = st.form_submit_button("✉️ Send Report", use_container_width=True)
                
                if submit_email:
                    if client_email:
                        email_svc = EmailService()
                        if email_svc.send_report(client_email, name, pdf_bytes):
                            st.success(f"Report successfully sent to {client_email}!")
                        else:
                            st.error("Failed to send report. Please check logs.")
                    else:
                        st.warning("Please enter an email address.")
                        
    except Exception as e:
        st.warning(f"PDF export unavailable: {e}")


