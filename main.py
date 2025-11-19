"""
Main entry point for the AI-Enhanced Resume Analyzer.
Supports CLI mode or polished GUI (launches if no args).
"""

import argparse
import json
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from typing import List
from analyzers.parser import parse_resume
from analyzers.scoring_engine import score_resume_master
from analyzers.keyword_engine import best_keywords_for_scoring
from utils.file_loader import load_resume_file
import threading
import time  # For status timestamps
import os

# Optional: default sample resume to test quickly (local path from your workspace)
DEFAULT_TEST_RESUME = "/mnt/data/Resume-Sample-1-Software-Engineer.pdf"


def run_cli(args_resume_file: str, args_job_desc: str, args_keywords: str):
    """CLI mode: extract, parse, score, output JSON and print summary."""
    job_desc = ""
    # job_desc arg could be a file path or inline text
    if args_job_desc:
        # If it's a path to a file, try to read it
        if os.path.exists(args_job_desc):
            try:
                with open(args_job_desc, "r", encoding="utf-8") as f:
                    job_desc = f.read().strip()
            except Exception:
                job_desc = args_job_desc.strip()
        else:
            job_desc = args_job_desc.strip()

    # If keywords provided (comma-separated), convert to a small job_desc for scoring
    if args_keywords and args_keywords.strip():
        # Only use provided keywords if job_desc empty
        if not job_desc:
            kw_list = [k.strip() for k in args_keywords.split(",") if k.strip()]
            if kw_list:
                job_desc = " ".join(kw_list)

    # Load resume file
    print("Extracting text from resume...")
    text, file_type = load_resume_file(args_resume_file)
    if not text:
        print(f"Error: Failed to extract from {file_type}.")
        return
    print(f"Successfully extracted from {file_type}.")

    # Parse resume
    print("AI parsing resume sections...")
    parsed = parse_resume(text)
    if "error" in parsed:
        print(f"Error: {parsed['error']}")
        return

    # Score resume (job_desc may be empty -> scoring engine auto-generates keywords)
    print("AI scoring resume...")
    result = score_resume_master(parsed, job_desc)

    # Build JSON output
    output_data = {
        "parsed": parsed,
        "scores": {
            "final_score": result["final_score"],
            "breakdown": result["breakdown"],
            "diagnostics": result.get("diagnostics", {})
        },
        "job_desc_used": bool(job_desc),
        "job_desc_text": job_desc if job_desc else None
    }

    # Print a compact summary
    print("\n" + "=" * 60)
    print("AI RESUME ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Name: {parsed.get('name') or 'Not found'}")
    print(f"Email(s): {', '.join(parsed.get('email', [])) or 'Not found'}")
    print(f"Phone(s): {', '.join(parsed.get('phone', [])) or 'Not found'}")
    print(f"Skills: {', '.join(parsed.get('skills', [])[:8])}{'...' if len(parsed.get('skills', [])) > 8 else ''}")
    print(f"Education: {len(parsed.get('education', []))} entries")
    print(f"Experience: {len(parsed.get('experience', []))} entries")
    print("\nScores:")
    print(f"  Total Score: {result['final_score']}/100")
    print("  Breakdown:")
    for k, v in result["breakdown"].items():
        print(f"    {k}: {round(v,2)}")
    print("=" * 60)

    # Save JSON
    json_file = "ai_resume_analysis.json"
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        print(f"\nDetailed AI analysis saved to {json_file}")
    except Exception as e:
        print(f"Error saving JSON: {e}")


def analyze_in_thread(gui_vars):
    """Run analysis in background; update progress."""
    gui_vars["status_label"].config(text="Analyzing... (This may take a few seconds)")
    gui_vars["progress_bar"].start()

    try:
        resume_path = gui_vars["resume_path"].get()
        job_desc_text = gui_vars["job_desc_text"].get("1.0", tk.END).strip()
        use_default_keywords = gui_vars["use_keywords_var"].get()

        if not resume_path:
            raise ValueError("Please upload a resume PDF.")

        text, file_type = load_resume_file(resume_path)
        if not text:
            raise ValueError(f"Failed to extract from {file_type}. Check file.")

        parsed = parse_resume(text)
        if "error" in parsed:
            raise ValueError(parsed["error"])

        # Determine job_desc passed to scoring engine:
        # If user provided JD text, use it.
        # If not, and use_default_keywords is True, pass empty JD -> engine auto-generates keywords from resume.
        # If not and use_default_keywords False, but job_desc_text empty, still pass empty JD (auto).
        if job_desc_text:
            job_desc = job_desc_text
        else:
            job_desc = ""  # allow automatic keyword generation inside scoring engine

        # Score
        result = score_resume_master(parsed, job_desc)

        output_data = {
            "parsed": parsed,
            "scores": {
                "final_score": result["final_score"],
                "breakdown": result["breakdown"],
                "diagnostics": result.get("diagnostics", {})
            },
            "job_desc_used": bool(job_desc),
            "job_desc_text": job_desc if job_desc else None
        }

        # Format output for GUI
        summary = "🚀 AI RESUME ANALYSIS SUMMARY\n"
        summary += "=" * 60 + "\n\n"
        summary += f"👤 Name: {parsed.get('name') or 'Not found'}\n"
        summary += f"📧 Email(s): {', '.join(parsed.get('email', [])) or 'Not found'}\n"
        summary += f"📱 Phone(s): {', '.join(parsed.get('phone', [])) or 'Not found'}\n"
        summary += f"🛠️  Skills: {', '.join(parsed.get('skills', [])[:8])}{'...' if len(parsed.get('skills', [])) > 8 else ''}\n"
        summary += f"🎓 Education: {len(parsed.get('education', []))} entries\n"
        summary += f"💼 Experience: {len(parsed.get('experience', []))} entries\n\n"

        summary += "📊 SCORES:\n"
        summary += f"  ⭐ Total Score: {result['final_score']}/100\n\n"
        summary += "🔍 Score Breakdown:\n"
        for k, v in result["breakdown"].items():
            summary += f"  • {k}: {round(v, 2)}\n"

        summary += "\n" + "=" * 60 + "\n"
        summary += f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}"

        # Update GUI
        gui_vars["output_text"].delete("1.0", tk.END)
        gui_vars["output_text"].insert("1.0", summary)
        gui_vars["status_label"].config(text=f"Analysis complete at {time.strftime('%H:%M:%S')}.")
        gui_vars["output_data"] = output_data

    except Exception as e:
        messagebox.showerror("Analysis Error", str(e))
        gui_vars["status_label"].config(text=f"Error at {time.strftime('%H:%M:%S')}: {str(e)[:80]}...")
    finally:
        gui_vars["progress_bar"].stop()


def save_json(gui_vars):
    """Save JSON from analysis."""
    if "output_data" not in gui_vars or not gui_vars["output_data"]:
        messagebox.showwarning("No Data", "Run analysis first!")
        return

    try:
        with open("ai_resume_analysis.json", "w", encoding="utf-8") as f:
            json.dump(gui_vars["output_data"], f, indent=4, ensure_ascii=False)
        messagebox.showinfo("Saved", "Analysis saved to ai_resume_analysis.json")
        gui_vars["status_label"].config(text=f"JSON saved at {time.strftime('%H:%M:%S')}.")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))


def clear_results(gui_vars):
    """Clear output and reset."""
    gui_vars["output_text"].delete("1.0", tk.END)
    gui_vars["output_data"] = None
    gui_vars["status_label"].config(text="Results cleared. Ready for new analysis!")


def launch_gui():
    """Launch the polished Tkinter GUI."""
    root = tk.Tk()
    root.title("AI Resume Analyzer - Pro Edition")
    root.geometry("900x900")  # Bigger starting size
    root.configure(bg="#f8f9fa")  # Light gray bg for modern feel

    # Modern theme for ttk
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TButton", font=("Segoe UI", 10), padding=10)
    style.configure("TLabel", font=("Segoe UI", 10))
    style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))

    gui_vars = {}

    # Header
    header_frame = tk.Frame(root, bg="#007BFF", height=60)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    tk.Label(
        header_frame,
        text="🤖 AI Resume Analyzer",
        font=("Segoe UI", 18, "bold"),
        fg="white",
        bg="#007BFF",
    ).pack(expand=True)

    # Main Content Frame (with padding)
    main_frame = tk.Frame(root, bg="#f8f9fa", padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Resume Upload Card
    upload_card = tk.LabelFrame(
        main_frame,
        text="📁 Upload Resume",
        font=("Segoe UI", 12, "bold"),
        bg="white",
        relief=tk.RIDGE,
        bd=1,
        padx=15,
        pady=10,
    )
    upload_card.pack(fill=tk.X, pady=(0, 15))
    gui_vars["resume_path"] = tk.StringVar()
    ttk.Entry(upload_card, textvariable=gui_vars["resume_path"], width=70, state="readonly").pack(pady=5)
    ttk.Button(
        upload_card,
        text="Browse PDF",
        command=lambda: gui_vars["resume_path"].set(
            filedialog.askopenfilename(title="Select PDF Resume", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        ),
    ).pack(pady=5)
    # Quick test button to use the default test resume if available
    if os.path.exists(DEFAULT_TEST_RESUME):
        ttk.Button(upload_card, text="Use Test Resume", command=lambda: gui_vars["resume_path"].set(DEFAULT_TEST_RESUME)).pack(pady=5)

    # Job Description Card
    job_card = tk.LabelFrame(
        main_frame,
        text="📝 Job Description (Optional for AI Scoring)",
        font=("Segoe UI", 12, "bold"),
        bg="white",
        relief=tk.RIDGE,
        bd=1,
        padx=15,
        pady=10,
    )
    job_card.pack(fill=tk.X, pady=(0, 15))
    gui_vars["job_desc_text"] = scrolledtext.ScrolledText(job_card, height=5, width=80, font=("Segoe UI", 10))
    gui_vars["job_desc_text"].pack(pady=5)
    gui_vars["use_keywords_var"] = tk.BooleanVar(value=True)
    ttk.Checkbutton(job_card, text="Auto-generate keywords from resume (recommended)", variable=gui_vars["use_keywords_var"]).pack(pady=5)

    # Buttons Row
    button_frame = tk.Frame(main_frame, bg="#f8f9fa")
    button_frame.pack(pady=10)

    def start_analysis():
        threading.Thread(target=analyze_in_thread, args=(gui_vars,), daemon=True).start()

    analyze_btn = tk.Button(
        button_frame,
        text="🚀 Analyze Resume",
        command=start_analysis,
        bg="#007BFF",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=20,
        pady=8,
        relief=tk.FLAT,
    )
    analyze_btn.pack(side=tk.LEFT, padx=(0, 10))

    save_btn = tk.Button(
        button_frame,
        text="💾 Save JSON",
        command=lambda: save_json(gui_vars),
        bg="#28a745",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=20,
        pady=8,
        relief=tk.FLAT,
    )
    save_btn.pack(side=tk.LEFT, padx=(0, 10))

    clear_btn = tk.Button(
        button_frame,
        text="🗑️ Clear Results",
        command=lambda: clear_results(gui_vars),
        bg="#dc3545",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=20,
        pady=8,
        relief=tk.FLAT,
    )
    clear_btn.pack(side=tk.LEFT)

    # Progress Bar
    gui_vars["progress_bar"] = ttk.Progressbar(main_frame, mode="indeterminate", length=400)
    gui_vars["progress_bar"].pack(pady=10)

    # Results Card (Bigger!)
    results_card = tk.LabelFrame(
        main_frame,
        text="📊 Analysis Results",
        font=("Segoe UI", 12, "bold"),
        bg="white",
        relief=tk.RIDGE,
        bd=1,
        padx=15,
        pady=10,
    )
    results_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    gui_vars["output_text"] = scrolledtext.ScrolledText(results_card, height=25, width=90, font=("Segoe UI", 10), bg="#f9f9f9", relief=tk.SUNKEN, bd=1)
    gui_vars["output_text"].pack(fill=tk.BOTH, expand=True)

    # Status Bar
    gui_vars["status_label"] = tk.Label(
        main_frame,
        text="Ready to upload and analyze! 👋",
        relief=tk.SUNKEN,
        anchor=tk.W,
        bg="#e9ecef",
        padx=10,
        pady=5,
        font=("Segoe UI", 9),
    )
    gui_vars["status_label"].pack(side=tk.BOTTOM, fill=tk.X)

    # Store output_data
    gui_vars["output_data"] = None

    # Hover effects for tk.Buttons
    def on_enter(e, btn, hover_color):
        btn.configure(bg=hover_color)

    def on_leave(e, btn, base_color):
        btn.configure(bg=base_color)

    analyze_btn.bind("<Enter>", lambda e: on_enter(e, analyze_btn, "#0056b3"))
    analyze_btn.bind("<Leave>", lambda e: on_leave(e, analyze_btn, "#007BFF"))
    save_btn.bind("<Enter>", lambda e: on_enter(e, save_btn, "#218838"))
    save_btn.bind("<Leave>", lambda e: on_leave(e, save_btn, "#28a745"))
    clear_btn.bind("<Enter>", lambda e: on_enter(e, clear_btn, "#c82333"))
    clear_btn.bind("<Leave>", lambda e: on_leave(e, clear_btn, "#dc3545"))

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="AI-Enhanced Resume Analyzer.")
    parser.add_argument("resume_file", nargs="?", help="Path to resume (PDF, DOCX, TXT)")
    parser.add_argument("--job_desc", help="Path to job desc file (TXT) or inline text")
    parser.add_argument("--keywords", default="", help="Fallback keywords (comma-separated)")
    args = parser.parse_args()

    if args.resume_file is None:
        launch_gui()
    else:
        # If user passed "test" we use the default test resume (if present)
        resume_path = args.resume_file
        if resume_path.lower() == "test" and os.path.exists(DEFAULT_TEST_RESUME):
            resume_path = DEFAULT_TEST_RESUME
        run_cli(resume_path, args.job_desc, args.keywords)


if __name__ == "__main__":
    main()
