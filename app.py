
import base64
import hashlib
import hmac
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------- CONFIGURATION --------------------
st.set_page_config(
    page_title="EduVista | Attendance Predictor",
    page_icon="🎓",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
STUDENTS_FILE = BASE_DIR / "students.csv"
ATTENDANCE_FILE = BASE_DIR / "attendance.csv"




# -------------------- DESIGN AND THEME --------------------
BG = "#100D24"
PANEL = "#1C1735"
TEXT = "#F5F3FF"
MUTED = "#C4BBDD"
BORDER = "#39305C"
PRIMARY = "#A78BFA"
CHART_TEMPLATE = "plotly_dark"

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #100D24, #171331, #20143B);
    color: #F5F3FF;
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    background: #17132E;
    border-right: 1px solid #39305C;
}

[data-testid="stSidebar"] * {
    color: #F5F3FF;
}

.block-container {
    max-width: 1400px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.stApp h1, .stApp h2, .stApp h3 {
    color: #F5F3FF !important;
    font-weight: 750;
}

.stApp p,
.stApp label,
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stWidgetLabel"] p {
    color: #D2CBE8 !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #251C46, #1C1735);
    border: 1px solid #514078;
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 6px 22px rgba(8, 5, 25, 0.25);
}

[data-testid="stMetricLabel"] {
    color: #C4BBDD !important;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #C4B5FD !important;
    font-weight: 800;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div {
    background: #17132E;
    border: 1px solid #514078;
    border-radius: 11px;
}

.stApp input, .stApp textarea {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(100deg, #7C3AED, #6366F1);
    color: #FFFFFF !important;
    border: none;
    border-radius: 11px;
    padding: 0.7rem 1.2rem;
    font-weight: 700;
    transition: all 0.2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background: linear-gradient(100deg, #8B5CF6, #818CF8);
    box-shadow: 0 5px 20px rgba(139, 92, 246, 0.3);
}

[data-testid="stForm"] {
    background: #1C1735;
    border: 1px solid #514078;
    border-radius: 20px;
    padding: 24px;
}

[data-testid="stDataFrame"] {
    background: #1C1735;
    border: 1px solid #39305C;
    border-radius: 12px;
}

hr {
    border-color: #39305C;
}

[data-testid="stAlert"] {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)



# -------------------- DATA LOADING --------------------
@st.cache_data
def load_data():
    students = pd.read_csv(STUDENTS_FILE, dtype=str).fillna("")
    attendance = pd.read_csv(ATTENDANCE_FILE)

    required_students = {
        "student_id", "name", "username", "password_hash"
    }
    required_attendance = {
        "student_id", "subject", "total_classes_scheduled",
        "classes_completed", "classes_attended"
    }

    if not required_students.issubset(students.columns):
        raise ValueError("students.csv has incorrect column names.")

    if not required_attendance.issubset(attendance.columns):
        raise ValueError("attendance.csv has incorrect column names.")

    for col in [
        "total_classes_scheduled", "classes_completed", "classes_attended"
    ]:
        attendance[col] = pd.to_numeric(attendance[col], errors="raise")

    if students["username"].duplicated().any():
        raise ValueError("Each username in students.csv must be unique.")

    if attendance.duplicated(["student_id", "subject"]).any():
        raise ValueError("Duplicate student-subject records found.")

    if not attendance["student_id"].isin(students["student_id"]).all():
        raise ValueError("attendance.csv contains an unknown student ID.")

    if (
        (attendance["total_classes_scheduled"] <= 0).any()
        or (attendance["classes_completed"] < 0).any()
        or (attendance["classes_attended"] < 0).any()
        or (
            attendance["classes_attended"]
            > attendance["classes_completed"]
        ).any()
        or (
            attendance["classes_completed"]
            > attendance["total_classes_scheduled"]
        ).any()
    ):
        raise ValueError("Invalid attendance numbers in attendance.csv.")

    return students, attendance


def verify_password(password, stored_hash):
    """Verify the PBKDF2 hashes used in the supplied sample CSV."""
    try:
        algorithm, iterations, salt_text, digest_text = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False



# -------------------- LOGIN --------------------
if "student_id" not in st.session_state:
    st.session_state.student_id = None

st.sidebar.title("🎓 EduVista")
st.sidebar.caption("Student Attendance Intelligence")

if st.session_state.student_id is None:
    try:
        students, attendance = load_data()
    except Exception as error:
        st.error(f"Unable to load CSV files: {error}")
        st.stop()

    st.markdown("""
    <style>
    .stApp {
        background:
            radial-gradient(ellipse at 10% 15%, #20265b 0%, transparent 40%),
            radial-gradient(ellipse at 90% 85%, #351858 0%, transparent 38%),
            #0b1020;
    }

    .login-hero {
        background: linear-gradient(145deg, #252b66, #512b83 55%, #173b65);
        padding: 38px 30px;
        border-radius: 24px;
        min-height: 390px;
        border: 1px solid rgba(255,255,255,0.16);
        box-shadow: 0 20px 55px rgba(0,0,0,0.25);
        color: white;
        position: relative;
        overflow: hidden;
    }

    .login-hero h1 {
        color: white;
        font-size: 35px;
        line-height: 1.2;
        margin: 20px 0 12px 0;
    }

    .login-hero p {
        color: #dbeafe;
        font-size: 15px;
        line-height: 1.8;
    }

    .hero-tag {
        display: inline-block;
        padding: 7px 13px;
        border-radius: 30px;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.18);
        color: #c4f1ff;
        font-size: 12px;
        letter-spacing: 1px;
    }

    .hero-stat {
        margin-top: 28px;
        padding: 15px;
        border-radius: 14px;
        background: rgba(255,255,255,0.09);
        border: 1px solid rgba(255,255,255,0.13);
    }

    .hero-stat strong {
        display: block;
        font-size: 17px;
        color: #ffffff;
        margin-bottom: 4px;
    }

    .hero-stat span {
        color: #dbeafe;
        font-size: 12px;
    }

    .login-heading {
        color: #f8fafc;
        font-size: 29px;
        font-weight: 750;
        margin-top: 10px;
        margin-bottom: 4px;
    }

    .login-subheading {
        color: #a5b4d0;
        margin-bottom: 25px;
        font-size: 14px;
    }

    div[data-testid="stForm"] {
        background: rgba(20, 27, 52, 0.88);
        border: 1px solid #303b61;
        border-radius: 20px;
        padding: 26px;
        box-shadow: 0 15px 40px rgba(0,0,0,0.2);
    }

    div[data-testid="stTextInput"] label {
        color: #dbeafe !important;
        font-weight: 600;
    }

    div[data-testid="stTextInput"] input {
        background: #111a32 !important;
        color: #ffffff !important;
        border: 1px solid #3b4970 !important;
        border-radius: 11px !important;
        min-height: 46px;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #67e8f9 !important;
        box-shadow: 0 0 0 2px rgba(103,232,249,0.15) !important;
    }

    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(100deg, #6366f1, #8b5cf6, #06b6d4);
        color: white;
        border: none;
        border-radius: 11px;
        min-height: 48px;
        font-weight: 700;
        transition: all 0.2s ease;
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        border: 1px solid #a5f3fc;
        box-shadow: 0 5px 22px rgba(99,102,241,0.35);
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:35px'></div>", unsafe_allow_html=True)

    left, gap, right = st.columns([1.05, 0.12, 1])

    with left:
        st.markdown("""
        <div class="login-hero">
            <div class="hero-tag">✦ SMART CAMPUS • SMARTER FUTURE</div>
            <h1>Your Attendance.<br>Your Progress.<br>Your Future.</h1>
            <p>
                Take control of your academic journey.
                Track your attendance, explore future scenarios,
                and make smarter decisions before your next class.
            </p>
            <div class="hero-stat">
                <strong>◈ Attendance Intelligence</strong>
                <span>Understand your current attendance at a glance.</span>
            </div>
            <div class="hero-stat">
                <strong>↗ Future Attendance Forecast</strong>
                <span>See how attending or skipping classes affects you.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with gap:
        st.write("")

    with right:
        st.markdown("<div style='height:35px'></div>", unsafe_allow_html=True)
        st.markdown("<div class='login-heading'>Welcome back 👋</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='login-subheading'>Sign in to continue to your student dashboard.</div>",
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            submitted = st.form_submit_button(
                "Sign In  →",
                type="primary",
                use_container_width=True
            )

        if submitted:
            matching = students[
                students["username"].str.strip().str.casefold()
                == username.strip().casefold()
            ]

            if (
                not matching.empty
                and verify_password(
                    password,
                    matching.iloc[0]["password_hash"]
                )
            ):
                st.session_state.student_id = matching.iloc[0]["student_id"]
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

        st.markdown(
            "<p style='text-align:center;color:#8190b2;font-size:12px;margin-top:20px;'>"
            "SECURE STUDENT ACCESS · ED UVISTA"
            "</p>".replace("ED UVISTA", "EDUVISTA"),
            unsafe_allow_html=True
        )

        with st.expander("Demo login details"):
            st.write(
                "Sample usernames: aarav, meera, rohan, ananya, kabir, "
                "ishita, aditya, sana, vihaan, diya, arjun, kiara, reyansh, "
                "tara, dev, nisha, karthik, myra, advait, aisha, pranav, "
                "zoya, dhruv, navya, ibrahim, saanvi, yash, ritika, manav, lavanya."
            )
            st.code("Demo password: Demo@123")

    st.stop()


# -------------------- PERSONAL DASHBOARD --------------------
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.student_id = None
    st.rerun()

try:
    students, attendance = load_data()
except Exception as error:
    st.error(f"Unable to load CSV files: {error}")
    st.stop()

student_id = st.session_state.student_id
student_rows = students[students["student_id"] == student_id]

if student_rows.empty:
    st.session_state.student_id = None
    st.error("Student account not found. Please log in again.")
    st.stop()

student = student_rows.iloc[0]
my_data = attendance[
    attendance["student_id"] == student_id
].copy()

if my_data.empty:
    st.warning("No attendance records are available for your account.")
    st.stop()

my_data["attendance_pct"] = (
    my_data["classes_attended"]
    / my_data["classes_completed"].replace(0, float("nan"))
    * 100
).fillna(0)

my_data["classes_missed"] = (
    my_data["classes_completed"] - my_data["classes_attended"]
)

st.title("🎓 EduVista Dashboard")
st.write(f"Welcome, **{student['name']}**!")
st.caption(f"Student ID: {student_id}")

# -------------------- SUBJECT SELECTOR --------------------
subjects = my_data["subject"].tolist()
selected_subject = st.selectbox("Choose a subject", subjects)

record = my_data[my_data["subject"] == selected_subject].iloc[0]

scheduled = int(record["total_classes_scheduled"])
completed = int(record["classes_completed"])
attended = int(record["classes_attended"])
missed = int(record["classes_missed"])
remaining = scheduled - completed
current_pct = attended / completed * 100 if completed else 0

st.subheader(f"Attendance Overview — {selected_subject}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Classes Scheduled", scheduled)
c2.metric("Classes Completed", completed)
c3.metric("Classes Attended", attended)
c4.metric("Current Attendance", f"{current_pct:.2f}%")

st.progress(min(current_pct / 100, 1.0))

if current_pct >= 85:
    st.success("Attendance status: Good")
elif current_pct >= 75:
    st.warning("Attendance status: Monitor your attendance")
else:
    st.error("Attendance status: Low attendance")



# -------------------- FUTURE ATTENDANCE CALCULATOR --------------------
st.subheader("🔮 Future Attendance Predictor")

st.write(
    f"There are **{remaining}** scheduled classes remaining "
    f"for {selected_subject}."
)

if remaining > 0:
    col1, col2 = st.columns(2)

    with col1:
        skip_count = st.number_input(
            "Upcoming classes you will skip",
            min_value=0,
            max_value=remaining,
            value=min(2, remaining),
            step=1,
            key=f"skip_{selected_subject}"
        )

    with col2:
        attend_count = st.number_input(
            "Upcoming classes you will attend",
            min_value=0,
            max_value=remaining - int(skip_count),
            value=remaining - int(skip_count),
            step=1,
            key=f"attend_{selected_subject}"
        )

    scenario_classes = int(skip_count) + int(attend_count)
    future_attended = attended + int(attend_count)
    future_completed = completed + scenario_classes

    projected_pct = (
        future_attended / future_completed * 100
        if future_completed > 0 else 0
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Current Attendance", f"{current_pct:.2f}%")
    metric2.metric("Projected Attendance", f"{projected_pct:.2f}%")
    metric3.metric(
        "Classes Skipped",
        int(skip_count)
    )

    if projected_pct >= 75:
        st.success("Your projected attendance is at least 75%.")
    else:
        st.error("Your projected attendance is below 75%.")

    st.caption(
        "Only classes included in this scenario are counted. "
        "Unspecified future classes are not included."
    )
else:
    projected_pct = current_pct
    st.info("All scheduled classes have been completed.")

# -------------------- IMPROVED SUBJECT GRAPH --------------------
st.subheader("📊 Subject-wise Attendance Analysis")

chart_data = my_data.copy()

chart_data["Current Attendance (%)"] = (
    chart_data["classes_attended"]
    / chart_data["classes_completed"].replace(0, float("nan"))
    * 100
).fillna(0).round(2)

# Project each subject if the student attends all remaining classes.
chart_data["Projected Attendance (%)"] = (
    chart_data["classes_attended"]
    + chart_data["total_classes_scheduled"]
    - chart_data["classes_completed"]
) / chart_data["total_classes_scheduled"] * 100

chart_data["Projected Attendance (%)"] = (
    chart_data["Projected Attendance (%)"].clip(0, 100).round(2)
)

graph_data = chart_data.melt(
    id_vars=["subject"],
    value_vars=[
        "Current Attendance (%)",
        "Projected Attendance (%)"
    ],
    var_name="Attendance Type",
    value_name="Percentage"
)

fig = px.bar(
    graph_data,
    x="subject",
    y="Percentage",
    color="Attendance Type",
    barmode="group",
    text="Percentage",
    title="Current vs Projected Attendance by Subject",
    labels={
        "subject": "Subject",
        "Percentage": "Attendance (%)"
    },
    
    
    color_discrete_map={
    "Current Attendance (%)": "#8B5CF6",
    "Projected Attendance (%)": "#22D3EE"
     }


)

fig.add_hline(
    y=75,
    line_dash="dash",
    line_color="#F59E0B",
    annotation_text="75% reference"
)

fig.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside",
    cliponaxis=False
)

fig.update_layout(
    template=CHART_TEMPLATE,
    paper_bgcolor=PANEL,
    plot_bgcolor=PANEL,
    font=dict(color=TEXT),
    yaxis_range=[0, 115],
    xaxis_tickangle=-20,
    legend_title_text="",
    margin=dict(t=80, b=100)
)

st.plotly_chart(fig, use_container_width=True)

# -------------------- ALL SUBJECT RECORDS --------------------
st.subheader("📚 Your Subject Records")

summary = chart_data[
    [
        "subject",
        "total_classes_scheduled",
        "classes_completed",
        "classes_attended",
        "classes_missed",
        "Current Attendance (%)",
        "Projected Attendance (%)"
    ]
].copy()

st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True,
    column_config={
        "subject": "Subject",
        "total_classes_scheduled": "Total Scheduled",
        "classes_completed": "Completed",
        "classes_attended": "Attended",
        "classes_missed": "Missed",
        "Current Attendance (%)": st.column_config.NumberColumn(
            "Current Attendance",
            format="%.2f%%"
        ),
        "Projected Attendance (%)": st.column_config.NumberColumn(
            "Projected Attendance",
            format="%.2f%%"
        )
    }
)

st.caption(
    "EduVista calculates projected attendance using your CSV records. "
    "Projected values assume attendance at every remaining scheduled class; "
    "the what-if calculator lets you test a different scenario."
)


# -------------------- ATTENDANCE RECOVERY CALCULATOR --------------------
st.subheader("🎯 Attendance Recovery Calculator")

target_pct = 75

if current_pct >= target_pct:
    st.success(
        f"Your current attendance is {current_pct:.2f}%. "
        f"You have reached the {target_pct}% target."
    )
else:
    # Find the minimum consecutive classes needed to reach the target.
    required_classes = 0

    while (
        (attended + required_classes)
        / (completed + required_classes)
        * 100 < target_pct
    ):
        required_classes += 1

    st.warning(
        f"Attend the next {required_classes} consecutive classes "
        f"to reach at least {target_pct}% attendance in "
        f"{selected_subject}."
    )

    st.metric(
        "Additional Classes to Attend",
        required_classes
    )

st.caption(
    "This calculation assumes you attend every upcoming class "
    "until the target is reached. It does not change your CSV data."
)


# -------------------- DOWNLOAD ATTENDANCE REPORT --------------------
st.subheader("📥 Download Your Attendance Report")

download_report = chart_data[
    [
        "subject",
        "total_classes_scheduled",
        "classes_completed",
        "classes_attended",
        "classes_missed",
        "Current Attendance (%)",
        "Projected Attendance (%)"
    ]
].copy()

download_report.columns = [
    "Subject",
    "Total Classes Scheduled",
    "Classes Completed",
    "Classes Attended",
    "Classes Missed",
    "Current Attendance (%)",
    "Projected Attendance (%)"
]

csv_data = download_report.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download My Attendance Report",
    data=csv_data,
    file_name=f"attendance_report_{student_id}.csv",
    mime="text/csv",
    use_container_width=True
)
