# api/routes/notes.py
import os, json
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from api.deps import verify_api_key, SAVED_NOTES_PATH
from api.schemas import SaveNoteRequest, NotesListResponse, IngestItem

router = APIRouter(prefix="/notes", tags=["notes"])

def _load() -> Dict[str, List[dict]]:
    if not os.path.exists(SAVED_NOTES_PATH):
        return {}
    try:
        with open(SAVED_NOTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(data: Dict[str, List[dict]]):
    with open(SAVED_NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@router.post("/save")
def save_note(req: SaveNoteRequest, _: bool = Depends(verify_api_key)):
    data = _load()
    data.setdefault(req.date, [])
    exists = any((x.get("title")==req.title and x.get("url")==req.url) for x in data[req.date])
    if exists:
        return {"ok": True, "message": "Already saved"}
    data[req.date].append(req.dict(exclude={"date"}))
    _save(data)
    return {"ok": True, "message": "Saved"}

@router.get("/list/{date}", response_model=NotesListResponse)
def list_notes(date: str, _: bool = Depends(verify_api_key)):
    data = _load()
    items = data.get(date, [])
    # sort by relevance desc
    items.sort(key=lambda x: int(x.get("relevance", 0)), reverse=True)
    return NotesListResponse(date=date, items=[IngestItem(**it) for it in items])

@router.delete("/delete/{date}")
def delete_day(date: str, _: bool = Depends(verify_api_key)):
    data = _load()
    if date in data:
        del data[date]
        _save(data)
        return {"ok": True, "message": f"Deleted all notes for {date}"}
    raise HTTPException(status_code=404, detail="Date not found")
@router.post("/delete_one")
def delete_one_note(payload: dict, _: bool = Depends(verify_api_key)):
    """
    payload = {
      "date": "YYYY-MM-DD",
      "title": "...",   # optional but recommended
      "url": "..."      # optional but recommended
    }
    Match priority: title+url > title only > url only.
    """
    date = payload.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="date required")

    data = _load()
    items = data.get(date, [])
    if not items:
        raise HTTPException(status_code=404, detail="No notes for this date")

    title = payload.get("title")
    url = payload.get("url")

    def keep(x):
        # remove if both match; else try title/url match
        if title and url:
            return not (x.get("title") == title and x.get("url") == url)
        if title:
            return x.get("title") != title
        if url:
            return x.get("url") != url
        return True  # nothing to remove

    new_items = [x for x in items if keep(x)]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail="Note not found with given keys")

    data[date] = new_items
    _save(data)
    return {"ok": True, "message": "Note deleted"}

