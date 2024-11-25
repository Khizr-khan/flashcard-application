from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.templating import Jinja2Templates
from app.models import User, Subject, FlashCard
from app.database import get_db
from sentence_transformers import SentenceTransformer, util
import random
import csv
import os

# Initialize Jinja2 templates and SentenceTransformer model
templates = Jinja2Templates(directory="app/templates")
model = SentenceTransformer("all-MiniLM-L6-v2")

router = APIRouter()

# Dashboard: Display all subjects for the logged-in user
@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    subjects = db.query(Subject).filter(Subject.user_id == user_id).all()
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user, "subjects": subjects}
    )

# Create a new subject for the logged-in user
@router.post("/create_subject")
async def create_subject(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Not authenticated.")
    new_subject = Subject(name=name, user_id=user_id)
    db.add(new_subject)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

# Delete a subject for the logged-in user
@router.post("/delete_subject")
async def delete_subject(request: Request, subject_id: int = Form(...), db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    # Delete associated flashcards first
    db.query(FlashCard).filter(FlashCard.subject_id == subject_id).delete()
    db.delete(subject)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

# Redirect to flashcards management page for a subject
@router.post("/flashcards")
async def redirect_to_flashcards(subject_id: int = Form(...)):
    return RedirectResponse(url=f"/flashcards/{subject_id}", status_code=HTTP_303_SEE_OTHER)

# View flashcards for a specific subject
@router.get("/view_flashcards/{subject_id}")
async def view_flashcards(subject_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    flashcards = db.query(FlashCard).filter(FlashCard.subject_id == subject_id).all()
    return templates.TemplateResponse(
        "view_flashcards.html",
        {"request": request, "flashcards": flashcards, "subject_id": subject_id, "subject_name": subject.name},
    )

# Add a new flashcard to a subject
@router.post("/add_flashcard")
async def add_flashcard(
    request: Request,
    card: str = Form(...),
    definition: str = Form(...),
    subject_id: int = Form(...),
    db: Session = Depends(get_db),
):
    new_flashcard = FlashCard(card=card, definition=definition, subject_id=subject_id)
    db.add(new_flashcard)
    db.commit()
    return templates.TemplateResponse(
        "flashcard_success.html",
        {"request": request, "message": "Flashcard added successfully!", "subject_id": subject_id},
    )

# Delete a flashcard
@router.post("/delete_flashcard")
async def delete_flashcard(flashcard_id: int = Form(...), db: Session = Depends(get_db)):
    flashcard = db.query(FlashCard).filter(FlashCard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found.")
    subject_id = flashcard.subject_id
    db.delete(flashcard)
    db.commit()
    return RedirectResponse(url=f"/view_flashcards/{subject_id}", status_code=HTTP_303_SEE_OTHER)

# Download all flashcards for a subject as CSV
@router.get("/download_flashcards/{subject_id}")
async def download_flashcards(subject_id: int, db: Session = Depends(get_db)):
    """
    Download all flashcards for a specific subject as a CSV file.
    """
    flashcards = db.query(FlashCard).filter(FlashCard.subject_id == subject_id).all()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()

    if subject:
        subject_name = subject.name
    else:
        raise HTTPException(status_code=404, detail="Subject not found.")

    if not flashcards:
        raise HTTPException(status_code=404, detail="No flashcards found for this subject.")

    # Create a CSV file with flashcards data
    file_path = f"flashcards_subject_{subject_name}.csv"
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Card", "Definition"])  # CSV headers
        for flashcard in flashcards:
            writer.writerow([flashcard.card, flashcard.definition])

    # Serve the file as a response
    return FileResponse(
        path=file_path,
        filename=f"flashcards_subject_{subject_name}.csv",
        media_type="text/csv",
    )


# Quiz: Randomly display flashcards for a subject
@router.post("/quiz")
async def quiz(
    request: Request,
    db: Session = Depends(get_db),
    subject_id: int = Form(...),
    num_questions: int = Form(default=None),
):
    flashcards = db.query(FlashCard).filter(FlashCard.subject_id == subject_id).all()
    if not flashcards:
        raise HTTPException(status_code=404, detail="No flashcards found for this subject.")

    if num_questions is None:
        # Initial form to ask how many questions to play
        return templates.TemplateResponse(
            "quiz_questions_form.html",
            {"request": request, "subject_id": subject_id, "max_questions": len(flashcards)}
        )

    # Limit the number of questions to the available flashcards
    num_questions = min(num_questions, len(flashcards))
    selected_flashcards = random.sample(flashcards, num_questions)

    return templates.TemplateResponse(
        "quiz.html",
        {"request": request, "flashcards": selected_flashcards, "subject_id": subject_id}
    )

# Submit quiz answers and evaluate
@router.post("/quiz/submit")
async def submit_quiz(
    request: Request,
    db: Session = Depends(get_db),
    subject_id: int = Form(...),
    flashcard_ids: list[int] = Form(...),
    answers: list[str] = Form(...),
):
    results = []
    correct_count = 0

    for flashcard_id, user_answer in zip(flashcard_ids, answers):
        flashcard = db.query(FlashCard).filter(FlashCard.id == flashcard_id).first()
        if not flashcard:
            continue

        embeddings = model.encode([user_answer, flashcard.definition])
        similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
        is_correct = similarity > 0.75

        if is_correct:
            correct_count += 1

        results.append({
            "question": flashcard.card,
            "actual_answer": flashcard.definition,
            "user_answer": user_answer,
            "is_correct": is_correct
        })

    return templates.TemplateResponse(
        "quiz_results.html",
        {"request": request, "results": results, "correct_count": correct_count, "total": len(flashcard_ids)}
    )

@router.get("/flashcards/{subject_id}")
async def manage_flashcards(subject_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    # Fetch the subject for the logged-in user
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    # Fetch flashcards for the subject
    flashcards = db.query(FlashCard).filter(FlashCard.subject_id == subject_id).all()
    return templates.TemplateResponse(
        "flashcards.html",
        {
            "request": request,
            "flashcards": flashcards,
            "subject_id": subject_id,
            "subject_name": subject.name,
        },
    )
