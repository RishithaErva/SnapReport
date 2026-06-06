# SnapReport by Snaphomz 🏠

SnapReport generates an AI-written real estate market report PDF for any ZIP code in under 90 seconds. 

Here is a detailed breakdown of exactly what I built, how the architecture evolved, the challenges I ran into, and where I plan to take this project next!

---

## What I Have Built 

### 1. The Streamlit Foundation & Multi-ZIP Support
I started by using **Streamlit** because it's the fastest way to get a working UI up and running without wrestling with frontend frameworks. Originally, the app only took one ZIP code. I refactored the entire flow so agents can input a comma-separated list of ZIP codes (like `90210, 10001, 75201`). The app now loops through each ZIP, fetching data and generating a unique section for every single one.

### 2. The AI Brain (Google Gemini Integration)
Instead of boring, templated text, I integrated the **Google Gemini API**. I engineered a specific prompt that takes the raw market numbers (median price, days on market, active listings) and writes a 3-paragraph narrative. It tells buyers why they need to hurry up, and tells sellers why they need to list *now*. 
* **The cool part:** If the Gemini API ever fails, I built a bulletproof fallback that uses Python f-strings to stitch together a highly professional backup narrative so the app *never* crashes.

### 3. Data Visualization with Plotly
Reading raw numbers is boring, so I added **Plotly** to generate visual trend charts. 
* I created a `generate_charts()` function that calculates a 6-month historical trend for both **Median Price** and **Inventory Months**.
* These aren't just rendered in the Streamlit UI; I used `kaleido` to convert these interactive Plotly graphs into static PNG byte streams so they could be injected directly into the final PDF.

### 4. The ReportLab PDF Engine
Generating the PDF was definitely a puzzle. I used `reportlab` because it's pure Python.
* I refactored the PDF generator to handle multiple ZIP codes by dynamically inserting `PageBreak` objects so each neighborhood gets its own clean page.
* I successfully embedded the generated Plotly chart images side-by-side above the AI narrative.

### 5. Abstracting the Data (RealEstateAPI & Fallbacks)
At first, all the market data was just hardcoded in a big dictionary in `app.py`. That was messy.
* I ripped that out and created a dedicated `RealEstateAPIService` class. 
* I set up the framework to hit `api.realestateapi.com`. But because I didn't have the exact API endpoint documentation, it kept throwing a `404 Not Found`.
* **The Pivot:** Instead of letting the app break, I built a massive `mock_data.json` file containing 40 major US cities. I set up a robust `try/except` block. Now, the app *tries* to hit the live API, catches the error gracefully, and seamlessly falls back to reading my local JSON file. 
* I even added little UI badges (`🟢 Live Market Data` vs `🟡 Demo Market Data`) so I always know where the data is coming from!

### 6. Email Delivery (SendGrid)
I wanted the agent to be able to email the PDF directly from the app. 
* I built an `EmailService` class integrating the **SendGrid Python SDK**. 
* I got the PDF attachment logic working perfectly (converting the PDF buffer to Base64). 
* **The Challenge:** SendGrid threw a `401 Unauthorized` error because my API key wasn't fully set up and the sender email wasn't verified.
* **The Pivot:** Just like the market data, I wrapped the email sender in a fallback block. If SendGrid fails, the code triggers a `time.sleep(1.5)` command to simulate network lag and flashes a `[DEMO MODE]` success message. The UI feels completely real and functional while I sort out the API keys!

### 7. Security (.env Variables)
I realized hardcoding API keys is a terrible practice. I integrated `python-dotenv`, created a local `.env` file, and refactored the entire app to pull the `GOOGLE_API_KEY`, `REALESTATE_API_KEY`, and `SENDGRID_API_KEY` securely from the environment.

---

## 🚀 Future Improvements 

Here are some imrovements i thought of implementing:

1. **Fixing the Live APIs **
   * **SendGrid**: I need to log into the SendGrid console, verify my sender identity (e.g., `ervarishitha@gmail.com`), generate a proper `SG.xxx` API key, and swap it into the `.env` file.
   * **RealEstateAPI**: I need to dig into their documentation, find the exact URL for the `/v2/PropertySearch` endpoint, and write an aggregation script that calculates the median price from the raw property data they return.

2. **Database Integration**
   * Right now, the app uses Streamlit's `st.session_state` to remember things temporarily. I want to add **Supabase** or **Firebase** to save the generated reports so agents can log in and view their past history.

3. **Cron Jobs / Scheduling**
   * The ultimate goal of SnapReport is automation. I want to add a feature where an agent enters a ZIP code *once*, and the app automatically runs a background cron job to email the updated PDF to their clients on the 1st of every month without them clicking anything.

4. **Interactive Maps**
   * I want to integrate the **Mapbox API** or **Google Maps Static API** to pull a high-res neighborhood map and stick it right at the top of the PDF header to make it look even more premium.

5. **Transitioning from Streamlit**
   * Streamlit is amazing for this MVP, but as I add user authentication and complex dashboard features, I might need to rebuild the frontend in **Next.js** and keep Python running purely as the backend API.

---

## 💻 How to Run This Project

### 1. Setup
Install all required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Set your API keys
Create a `.env` file in the root directory and add your keys (the app automatically loads them using `python-dotenv`):
```env
GOOGLE_API_KEY="your-gemini-key-here"
REALESTATE_API_KEY="your-realestate-key-here"
SENDGRID_API_KEY="your-sendgrid-key-here"
```

### 3. Run
Start the Streamlit server:
```bash
python3 -m streamlit run app.py
```

### 4. Demo ZIP codes
You can test the app with any of the 40 mock ZIP codes built into the fallback data. Here are a few to try:

| ZIP | Market |
|-----|--------|
| 90210 | Beverly Hills, CA |
| 10001 | Manhattan, NY |
| 75201 | Dallas, TX |
| 33139 | Miami Beach, FL |
| 60601 | Chicago, IL |
| 98101 | Seattle, WA |


## Deployed app

I have deployed the app on streamlit community cloud. You can access it here:

https://snaprepor-vuheeu2jfsv8fna84xwnrk.streamlit.app/