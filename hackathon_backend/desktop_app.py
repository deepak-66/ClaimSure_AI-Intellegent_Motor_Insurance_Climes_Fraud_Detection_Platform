import tkinter as tk
from tkinter import ttk, messagebox
import json
import urllib.request
import urllib.error
from datetime import date

API = "http://127.0.0.1:8000"


def api_request(path, method="GET", data=None):
    body = None
    headers = {}

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        API + path,
        data=body,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8")
        raise Exception(detail)
    except Exception:
        raise Exception(
            "Cannot connect to backend. Start the FastAPI server first."
        )


def submit_claim():
    try:
        claim = {
            "claimant_name": name_entry.get().strip(),
            "policy_number": policy_entry.get().strip(),
            "vehicle_registration": vehicle_entry.get().strip(),
            "accident_date": date_entry.get().strip(),
            "claim_amount": float(amount_entry.get()),
            "accident_description": description_entry.get("1.0", "end").strip()
        }

        result = api_request("/claims", "POST", claim)

        messagebox.showinfo(
            "Success",
            f"Claim submitted!\nClaim ID: {result['claim']['claim_id']}"
        )
        refresh_claims()

    except Exception as error:
        messagebox.showerror("Error", str(error))


def refresh_claims():
    try:
        result = api_request("/claims")
        claims_list.delete(0, tk.END)

        for claim in result["claims"]:
            claims_list.insert(
                tk.END,
                f"ID: {claim['claim_id']} | "
                f"{claim['claimant_name']} | "
                f"₹{claim['claim_amount']:,.2f} | "
                f"{claim['status']}"
            )

        status_label.config(
            text=f"Backend connected | Total claims: {result['total_claims']}"
        )

    except Exception as error:
        status_label.config(text="Backend disconnected")
        messagebox.showerror("Connection Error", str(error))


def selected_claim_id():
    selection = claims_list.curselection()

    if not selection:
        messagebox.showwarning(
            "Select a claim",
            "Please select a claim from the list first."
        )
        return None

    line = claims_list.get(selection[0])
    return int(line.split("|")[0].replace("ID:", "").strip())


def assess_risk():
    claim_id = selected_claim_id()
    if claim_id is None:
        return

    try:
        result = api_request(
            f"/claims/{claim_id}/risk-assessment",
            "POST"
        )

        messagebox.showinfo(
            "Risk Assessment",
            f"Claim ID: {claim_id}\n"
            f"Demo Risk Score: {result['demo_risk_score']}\n"
            f"Review Required: {result['review_required']}\n"
            f"Flags: {', '.join(result['flags']) or 'None'}\n\n"
            "This is a demonstration rule-based score, not proof of fraud."
        )

    except Exception as error:
        messagebox.showerror("Error", str(error))


def generate_summary():
    claim_id = selected_claim_id()
    if claim_id is None:
        return

    try:
        result = api_request(
            f"/claims/{claim_id}/ai-summary",
            "POST"
        )

        messagebox.showinfo("Claim Summary", result["summary"])

    except Exception as error:
        messagebox.showerror("Error", str(error))


def update_status():
    claim_id = selected_claim_id()
    if claim_id is None:
        return

    status = status_choice.get()

    try:
        result = api_request(
            f"/claims/{claim_id}/status",
            "POST",
            {"status": status}
        )

        messagebox.showinfo("Success", result["message"])
        refresh_claims()

    except Exception as error:
        messagebox.showerror("Error", str(error))


root = tk.Tk()
root.title("ClaimSure AI - Insurance Claims Management")
root.geometry("900x720")
root.minsize(750, 600)

title = ttk.Label(
    root,
    text="ClaimSure AI",
    font=("Arial", 22, "bold")
)
title.pack(pady=10)

subtitle = ttk.Label(
    root,
    text="Motor Insurance Claims Management System"
)
subtitle.pack()

form = ttk.LabelFrame(root, text="Submit a New Claim", padding=12)
form.pack(fill="x", padx=15, pady=10)

ttk.Label(form, text="Claimant Name").grid(row=0, column=0, sticky="w", padx=5, pady=5)
name_entry = ttk.Entry(form, width=30)
name_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(form, text="Policy Number").grid(row=0, column=2, sticky="w", padx=5, pady=5)
policy_entry = ttk.Entry(form, width=30)
policy_entry.grid(row=0, column=3, padx=5, pady=5)

ttk.Label(form, text="Vehicle Registration").grid(row=1, column=0, sticky="w", padx=5, pady=5)
vehicle_entry = ttk.Entry(form, width=30)
vehicle_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(form, text="Accident Date (YYYY-MM-DD)").grid(row=1, column=2, sticky="w", padx=5, pady=5)
date_entry = ttk.Entry(form, width=30)
date_entry.insert(0, date.today().isoformat())
date_entry.grid(row=1, column=3, padx=5, pady=5)

ttk.Label(form, text="Claim Amount (₹)").grid(row=2, column=0, sticky="w", padx=5, pady=5)
amount_entry = ttk.Entry(form, width=30)
amount_entry.grid(row=2, column=1, padx=5, pady=5)

ttk.Label(form, text="Accident Description").grid(row=3, column=0, sticky="nw", padx=5, pady=5)
description_entry = tk.Text(form, width=65, height=3)
description_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=5)

ttk.Button(
    form,
    text="Submit Claim",
    command=submit_claim
).grid(row=4, column=0, columnspan=4, pady=10)

claims_frame = ttk.LabelFrame(root, text="Submitted Claims", padding=10)
claims_frame.pack(fill="both", expand=True, padx=15, pady=5)

claims_list = tk.Listbox(claims_frame, height=10)
claims_list.pack(fill="both", expand=True, pady=5)

buttons = ttk.Frame(claims_frame)
buttons.pack(fill="x", pady=5)

ttk.Button(
    buttons,
    text="Refresh Claims",
    command=refresh_claims
).pack(side="left", padx=5)

ttk.Button(
    buttons,
    text="Assess Risk",
    command=assess_risk
).pack(side="left", padx=5)

ttk.Button(
    buttons,
    text="Generate Summary",
    command=generate_summary
).pack(side="left", padx=5)

status_choice = tk.StringVar(value="UNDER_REVIEW")

ttk.Label(buttons, text="New Status:").pack(side="left", padx=(10, 3))

ttk.Combobox(
    buttons,
    textvariable=status_choice,
    values=["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"],
    state="readonly",
    width=15
).pack(side="left", padx=3)

ttk.Button(
    buttons,
    text="Update Status",
    command=update_status
).pack(side="left", padx=5)

status_label = ttk.Label(root, text="Checking backend...")
status_label.pack(pady=8)

root.after(500, refresh_claims)
root.mainloop()