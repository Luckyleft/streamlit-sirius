import requests
import uuid
import json
import urllib.parse
import streamlit as st

# --- API Functions ---

def login(session, config):
    try:
        params = {
            "os": config['os'], "dm": config['dm'], "did": config['did'],
            "ua": "iPhone", "aid": "DealerApp", "aname": "SiriusXM Dealer",
            "chnl": "mobile", "plat": "ios", "aver": config['aver'],
            "atype": "native", "stype": "b2c", "kuid": "",
            "mfaid": "df7be3dc-e278-436c-b2f8-4cfde321df0a",
            "mfbaseid": "efb9acb6-daea-4f2f-aeb3-b17832bdd47b",
            "mfaname": "DealerApp", "sdkversion": "9.5.36", "sdktype": "js",
            "sessiontype": "I", "clientUUID": "1742536405634-41a8-0de0-125c",
            "rsid": "1742536405654-b954-784f-38d2", "svcid": "login_$anonymousProvider"
        }
        paramsStr = json.dumps(params, separators=(',', ':'))
        
        headers = {
            "X-Voltmx-Platform-Type": "ios",
            "Accept": "application/json",
            "X-Voltmx-App-Secret": "c086fca8646a72cf391f8ae9f15e5331",
            "X-Voltmx-SDK-Type": "js",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": config['ua_string'],
            "X-Voltmx-App-Key": "67cfe0220c41a54cb4e768723ad56b41",
            "X-Voltmx-ReportingParams": urllib.parse.quote(paramsStr, safe='$:,'),
        }
        
        response = session.post("https://dealerapp.siriusxm.com/authService/100000002/login", headers=headers)
        response.raise_for_status()
        
        res_json = response.json()
        token = res_json.get('claims_token', {}).get('value')
        if not token:
            st.error("Failed to retrieve claims_token from response.")
            st.stop()
        return token
    except Exception as e:
        st.error(f"Login Failed: {e}")
        st.stop()

def get_properties(session, config, auth_token):
    try:
        params = {
            "os": config['os'], "dm": config['dm'], "did": config['did'],
            "ua": "iPhone", "aid": "DealerApp", "aname": "SiriusXM Dealer",
            "plat": "ios", "aver": config['aver'], "svcid": "getProperties"
        }
        paramsStr = json.dumps(params, separators=(',', ':'))
        headers = {
            "X-Voltmx-Authorization": auth_token,
            "User-Agent": config['ua_string'],
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Voltmx-ReportingParams": urllib.parse.quote(paramsStr, safe='$:,'),
        }
        response = session.post("https://dealerapp.siriusxm.com/services/DealerAppService7/getProperties", headers=headers)
        return response.status_code
    except Exception as e:
        st.warning(f"Properties check failed, continuing... {e}")

def update_request(session, config, auth_token, endpoint, payload):
    try:
        headers = {
            "X-Voltmx-Authorization": auth_token,
            "User-Agent": config['ua_string'],
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Voltmx-DeviceId": config['did']
        }
        response = session.post(f"https://dealerapp.siriusxm.com/services/{endpoint}", headers=headers, data=payload)
        return response
    except Exception as e:
        st.error(f"Request to {endpoint} failed: {e}")
        return None

# --- UI Setup ---

st.set_page_config(page_title="Radio Refresher", page_icon="📻")
st.markdown("<h3 style='text-align:center;'>Radio Refresher</h3>", unsafe_allow_html=True)

with st.form("radio_form"):
    radio_id_input = st.text_input("Enter Radio ID or VIN:").strip().upper()
    submitted = st.form_submit_button("Submit")

if submitted:
    if not radio_id_input:
        st.error("Please enter a value.")
        st.stop()

    # Configuration Dictionary
    config = {
        "did": str(uuid.uuid4()),
        "dm": "iPhone 14 Pro",
        "os": "17.0",
        "aver": "3.1.0",
        "ua_string": "SiriusXM%20Dealer/3.1.0 CFNetwork/1568.200.51 Darwin/24.1.0"
    }

    session = requests.Session()

    with st.status("Processing Request...", expanded=True) as status:
        # 1. Login
        st.write("Authenticating...")
        auth_token = login(session, config)
        
        # 2. Setup Env
        st.write("Initializing session properties...")
        get_properties(session, config, auth_token)

        # 3. Determine Logic Flow
        if len(radio_id_input) == 17:
            st.write("Detected VIN. Refreshing via Vehicle Data...")
            # Example endpoint for VIN update
            res = update_request(session, config, auth_token, 
                               "USUpdateDeviceSATRefresh/updateDeviceSATRefreshWithPriority", 
                               {"vin": radio_id_input, "provisionType": "activate"})
            st.write(f"Server Response: {res.status_code if res else 'No Response'}")
            
        elif len(radio_id_input) in [8, 12]:
            st.write("Detected Radio ID. Sending Refresh...")
            res = update_request(session, config, auth_token, 
                               "USUpdateDeviceSATRefresh/updateDeviceSATRefreshWithPriority", 
                               {"deviceId": radio_id_input, "provisionType": "activate"})
            st.write(f"Server Response: {res.status_code if res else 'No Response'}")
            
        else:
            st.error("Invalid ID length. VINs are 17 chars; Radio IDs are 8 or 12.")
            st.stop()

        status.update(label="Process Complete!", state="complete")
    
    st.success("The refresh request has been sent to the SiriusXM gateway.")
