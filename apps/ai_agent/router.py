from apps.ai_agent.models import AIChat
from apps.ai_agent.prompts import CRUD_PROMPT
from apps.tasks.models import Task
from apps.tasks.schemas import FlowAI, FlowAIOut, TaskCreate, TaskUpdate
from apps.database import get_db
from apps.pagination import PaginatedResponse
from apps.ai_agent import crud as ai_crud
from apps.tasks import crud
from apps.users import crud as user_crud
from apps.boards import crud as board_crud
from apps.auth.dependencies import get_current_user
from apps.users.models import User
from apps.boards.schemas import BoardCreate

from services.groq import GroqAI
from sqlalchemy import update, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, status
import json
import re


router = APIRouter(
    prefix="/ai-chat",
    tags=["AI Chat"]
)

# --- AI Chat Endpoints ---
@router.post("/", response_model=FlowAIOut, status_code=status.HTTP_200_OK)
def ai_chat(
    ai_question : FlowAI,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Call the AI chat to create/update tasks or boards based on user input.

    Args:
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.
    """
    if ai_question.is_static:
        if ai_question.question.lower() == "create task":
            return {"message": "Please provide task details to create a new task."}

    # 0. Intercept structured form submission from the interactive task creation form
    if ai_question.question.startswith("__FORM_CREATE__"):
        try:
            form_json = ai_question.question[len("__FORM_CREATE__"):]
            form_data = json.loads(form_json)
            
            resolved_board_id = form_data.get("board_id")
            if form_data.get("board_name") and not resolved_board_id:
                board = board_crud.get_board_by_name(db, form_data["board_name"], current_user.id)
                if board:
                    resolved_board_id = board.id
            
            task_data = TaskCreate(
                title=form_data.get("title", "Untitled Task"),
                description=form_data.get("description"),
                status=form_data.get("status", "todo"),
                priority=form_data.get("priority", "medium"),
                tag=form_data.get("tag"),
                assignee_id=form_data.get("assignee_id"),
                board_id=resolved_board_id,
                position=0
            )
            task = crud.create_task(db, task_data=task_data, user_id=current_user.id)
            
            details = []
            details.append(f"**Title**: {task.title}")
            if task.description:
                details.append(f"**Description**: {task.description}")
            details.append(f"**Status**: {task.status}")
            details.append(f"**Priority**: {task.priority}")
            if task.tag:
                details.append(f"**Tag**: {task.tag}")
            if resolved_board_id:
                board_obj = board_crud.get_board_by_id(db, resolved_board_id)
                if board_obj:
                    details.append(f"**Board**: {board_obj.name}")
            
            details_str = "\n".join([f"• {d}" for d in details])
            answer = f"✅ Task created successfully! (ID: {task.id})\n\n{details_str}"
            
            current_chat = ai_crud.create_ai_chat(db, user_id=current_user.id, question=f"Create task: {task.title}")
            current_chat.answer = answer
            current_chat.ai_answer = json.dumps({"status": "created", "task_id": task.id})
            current_chat.task_id = task.id
            db.commit()
            db.refresh(current_chat)
            
            return FlowAIOut(
                question=f"Create task: {task.title}",
                is_static=False,
                answer=answer
            )
        except Exception as ex:
            import traceback
            traceback.print_exc()
            answer = f"Failed to create task from form: {str(ex)}"
            current_chat = ai_crud.create_ai_chat(db, user_id=current_user.id, question=ai_question.question[:50])
            current_chat.answer = answer
            db.commit()
            return FlowAIOut(question=ai_question.question[:50], is_static=False, answer=answer)

    # 1. Intercept Yes/No response for pending confirmations (Task Create, Board Create, Board Update, Task Delete)
    recent_chats = ai_crud.get_recent_ai_chats(db, user_id=current_user.id, limit=1)
    if recent_chats:
        last_chat = recent_chats[0]
        is_confirmation_prompt = last_chat.answer and (
            "Would you like me to create this task?" in last_chat.answer or
            "Would you like me to create this board?" in last_chat.answer or
            "Would you like me to update this board?" in last_chat.answer or
            "Are you sure you want to delete task" in last_chat.answer
        )
        if is_confirmation_prompt:
            cleaned_input = ai_question.question.strip().lower()
            if cleaned_input in ["yes", "y", "yeah", "sure", "ok", "do it", "yup", "yes please", "yes, please", "confirm", "delete it"]:
                try:
                    draft_data = json.loads(last_chat.ai_answer)
                    action_type = draft_data.get("action_type") or draft_data.get("ticket_type")

                    if action_type == "create_board":
                        name = draft_data.get("board_name") or "New Board"
                        description = draft_data.get("description")
                        columns = draft_data.get("columns") or ["todo", "in_progress", "done"]
                        
                        b_data = BoardCreate(name=name, description=description, columns=columns)
                        new_board = board_crud.create_board(db, board_data=b_data, owner_id=current_user.id)
                        answer = f"✅ Board '{new_board.name}' created successfully! (ID: {new_board.id})"

                    elif action_type == "update_board":
                        board_id = draft_data.get("board_id")
                        board = board_crud.get_board_by_id(db, board_id)
                        if board:
                            if draft_data.get("new_name"):
                                board.name = draft_data["new_name"]
                            if draft_data.get("description") is not None:
                                board.description = draft_data["description"]
                            if draft_data.get("columns"):
                                board.columns = draft_data["columns"]
                            db.commit()
                            db.refresh(board)
                            answer = f"✅ Board '{board.name}' updated successfully!"
                        else:
                            answer = "Board not found for update."

                    elif action_type == "delete_task":
                        task_id = draft_data.get("task_id")
                        task = crud.get_task_by_id(db, task_id)
                        if task:
                            task_title = task.title
                            db.execute(
                                update(AIChat)
                                .where(AIChat.task_id == task.id)
                                .values(task_id=None)
                            )
                            db.delete(task)
                            db.commit()
                            answer = f"🗑️ Task '{task_title}' (ID: {task_id}) deleted successfully!"
                        else:
                            answer = f"Task #{task_id} not found."

                    else: # Default: create task
                        title = draft_data.get("title") or "Untitled Task"
                        description = draft_data.get("description")
                        if not description or description.strip().lower() in ["no description provided.", "no description provided", "none", "null", "n/a", "no description"]:
                            description = f"Implement necessary fixes and task requirements for '{title}'. Review design layout, code implementation, and verify functionality."

                        board_name = draft_data.get("board_name")
                        priority = draft_data.get("priority", "medium")
                        tag = draft_data.get("tag") or "Task"
                        assignee = draft_data.get("assignee_id") or draft_data.get("assignee")
                        task_status = draft_data.get("status", "todo")
                        
                        resolved_board_id = None
                        if board_name:
                            board = board_crud.get_board_by_name(db, board_name, current_user.id)
                            if board:
                                resolved_board_id = board.id

                        resolved_assignee_id = None
                        if assignee is not None:
                            if isinstance(assignee, int):
                                resolved_assignee_id = assignee
                            elif isinstance(assignee, str) and assignee.strip():
                                found_user = user_crud.get_user_by_username(db, assignee.strip())
                                if found_user:
                                    resolved_assignee_id = found_user.id

                        task_data = TaskCreate(
                            title=title or "Untitled Task",
                            description=description,
                            status=task_status,
                            priority=priority,
                            tag=tag,
                            board_id=resolved_board_id,
                            assignee_id=resolved_assignee_id,
                            position=0
                        )
                        task = crud.create_task(db, task_data=task_data, user_id=current_user.id)
                        answer = f"✅ Task created successfully! (ID: {task.id}, Title: {task.title})"

                    current_chat = ai_crud.create_ai_chat(db, user_id=current_user.id, question=ai_question.question)
                    current_chat.answer = answer
                    current_chat.ai_answer = json.dumps({"status": "executed"})
                    db.commit()
                    db.refresh(current_chat)
                    
                    return FlowAIOut(
                        question=ai_question.question,
                        is_static=ai_question.is_static,
                        answer=answer
                    )
                except Exception as ex:
                    import traceback
                    traceback.print_exc()
                    db.rollback()
                    answer = f"Failed to process confirmation: {str(ex)}"
                    current_chat = ai_crud.create_ai_chat(db, user_id=current_user.id, question=ai_question.question)
                    current_chat.answer = answer
                    db.commit()
                    return FlowAIOut(question=ai_question.question, is_static=ai_question.is_static, answer=answer)
            
            elif cleaned_input in ["no", "n", "nope", "cancel", "don't do it", "no thanks", "no, thanks"]:
                answer = "Action cancelled."
                current_chat = ai_crud.create_ai_chat(db, user_id=current_user.id, question=ai_question.question)
                current_chat.answer = answer
                current_chat.ai_answer = json.dumps({"status": "cancelled"})
                db.commit()
                db.refresh(current_chat)
                
                return FlowAIOut(
                    question=ai_question.question,
                    is_static=ai_question.is_static,
                    answer=answer
                )

    # 2. Fetch and format up to 10 recent completed chat turns (oldest first)
    all_recent_chats = ai_crud.get_recent_ai_chats(db, user_id=current_user.id, limit=10)
    formatted_history = []
    for chat in reversed(all_recent_chats):
        formatted_history.append(f"User: {chat.question}\nAI: {chat.answer}")
    history_str = "\n\n".join(formatted_history) if formatted_history else "No previous history."

    # Format the question for the AI agent using the CRUD_PROMPT template
    question = CRUD_PROMPT.format(
        user_input=ai_question.question,
        user_input_history=history_str
    )

    ai_chat = ai_crud.create_ai_chat(db, user_id=current_user.id, question=ai_question.question)
   
    groq_ai = GroqAI()
    response = groq_ai.call_ai(question)
    
    try:
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*', '', cleaned_response)
        cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()
        
        response_data = json.loads(cleaned_response)
        if not isinstance(response_data, dict):
            raise ValueError("AI response must evaluate to a dictionary")
    except Exception as e:
        response_data = {
            "ticket_type": "other",
            "message": response
        }

    ticket_type = response_data.get("ticket_type", "other")
    
    hendler = {
        "create": "handle_create_task",
        "update": "handle_update_task",
        "move": "handle_move_task",
        "move_status": "handle_move_status",
        "assign": "handle_assign_task",
        "delete": "handle_delete_task",
        "create_board": "handle_create_board",
        "update_board": "handle_update_board",
        "other": "handle_other_request"
    }
    
    if ticket_type in hendler:
        handler_function = globals()[hendler[ticket_type]]
        return handler_function(db, current_user.id, response_data, ai_chat)

    answer = response_data.get("message") or "Request processed."
    ai_chat.ai_answer = response
    ai_chat.answer = answer
    db.commit()
    db.refresh(ai_chat)

    return FlowAIOut(
        question=ai_question.question,
        is_static=ai_question.is_static,
        answer=answer
    )

@router.get("/history", response_model=PaginatedResponse[FlowAIOut], status_code=status.HTTP_200_OK)
def ai_chat_history(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user), 
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1)
):
    res = ai_crud.get_ai_chat_history_paginated(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=page_size
    )
    for item in res.get("items", []):
        if item.answer is None:
            item.answer = ""
    return res


# --- Handler functions for AI operations ---

def handle_create_board(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Prompt user for confirmation before creating a new board."""
    try:
        board_name = response_data.get("board_name") or "New Board"
        description = response_data.get("description") or ""
        columns = response_data.get("columns") or ["todo", "in_progress", "done"]

        draft = {
            "action_type": "create_board",
            "board_name": board_name,
            "description": description,
            "columns": columns
        }

        ai_chat.ai_answer = json.dumps(draft)
        cols_str = ", ".join([c.replace("_", " ").title() for c in columns])

        answer = (
            f"📋 I prepared a draft for a new board:\n\n"
            f"* **Board Name**: {board_name}\n"
            f"* **Description**: {description or 'N/A'}\n"
            f"* **Columns**: {cols_str}\n\n"
            f"Would you like me to create this board? (Yes/No)"
        )

        ai_chat.answer = answer
        db.commit()
        db.refresh(ai_chat)
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to prepare board creation draft: {str(e)}")


def handle_update_board(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Prompt user for confirmation before updating an existing board."""
    try:
        board_name = response_data.get("board_name")
        board = None
        if board_name:
            board = board_crud.get_board_by_name(db, board_name, user_id)
        if not board:
            user_boards = board_crud.get_user_boards(db, user_id)
            if user_boards:
                board = user_boards[0]

        if not board:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="No target board found to update.")

        draft = {
            "action_type": "update_board",
            "board_id": board.id,
            "board_name": board.name,
            "new_name": response_data.get("new_name"),
            "description": response_data.get("description"),
            "columns": response_data.get("columns")
        }

        ai_chat.ai_answer = json.dumps(draft)

        changes = []
        if draft["new_name"]:
            changes.append(f"Rename to '{draft['new_name']}'")
        if draft["description"]:
            changes.append(f"Description → '{draft['description']}'")
        if draft["columns"]:
            changes.append(f"Columns → {', '.join(draft['columns'])}")

        changes_str = "\n".join([f"* {c}" for c in changes]) if changes else "* No major changes detected"

        answer = (
            f"✏️ I prepared an update draft for board '{board.name}':\n\n"
            f"{changes_str}\n\n"
            f"Would you like me to update this board? (Yes/No)"
        )

        ai_chat.answer = answer
        db.commit()
        db.refresh(ai_chat)
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to prepare board update draft: {str(e)}")


def find_task_by_title_or_id(db: Session, user_id: int, task_id: any, task_title: str | None) -> Task | None:
    """Helper to locate a task by ID or fuzzy title matching across user's tasks."""
    if task_id:
        try:
            t = crud.get_task_by_id(db, int(task_id))
            if t:
                return t
        except (ValueError, TypeError):
            pass

    if task_title:
        user_tasks = crud.get_tasks_by_user(db, user_id)
        if not user_tasks:
            from apps.tasks.models import Task
            user_tasks = list(db.scalars(select(Task)).all())
            
        clean_query = str(task_title).strip().lower()
        # 1. Exact match
        for t in user_tasks:
            if clean_query == t.title.lower().strip():
                return t
        # 2. Substring match
        for t in user_tasks:
            if clean_query in t.title.lower() or t.title.lower() in clean_query:
                return t
        # 3. Fuzzy ratio match using SequenceMatcher
        import difflib
        best_match = None
        best_ratio = 0.4
        for t in user_tasks:
            ratio = difflib.SequenceMatcher(None, clean_query, t.title.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = t
        if best_match:
            return best_match

    return None


def handle_delete_task(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Prompt user for confirmation before deleting a task."""
    try:
        task_id = response_data.get("task_id") or response_data.get("id")
        task_title = response_data.get("task_title") or response_data.get("title")
        task = find_task_by_title_or_id(db, user_id, task_id, task_title)

        if not task:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="Task not found to delete. Please specify a valid task ID or title.")

        draft = {
            "action_type": "delete_task",
            "task_id": task.id,
            "task_title": task.title
        }

        ai_chat.ai_answer = json.dumps(draft)

        answer = (
            f"⚠️ Are you sure you want to delete task '{task.title}' (ID: {task.id})?\n\n"
            f"This action cannot be undone. Please confirm: (Yes/No)"
        )

        ai_chat.answer = answer
        db.commit()
        db.refresh(ai_chat)
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to prepare delete task request: {str(e)}")


def handle_move_status(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Move task to a different status column directly."""
    try:
        task_id = response_data.get("task_id") or response_data.get("id")
        task_title = response_data.get("task_title") or response_data.get("title")
        new_status = response_data.get("status", "in_progress").lower().replace(" ", "_")
        
        task = find_task_by_title_or_id(db, user_id, task_id, task_title)

        if not task:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="Task not found. Please provide a valid task ID or title.")

        task.status = new_status
        if new_status in ["done", "completed"]:
            task.completed = True
        elif new_status in ["todo", "to_do", "in_progress"]:
            task.completed = False
            
        db.commit()
        db.refresh(task)

        formatted_status = new_status.replace("_", " ").title()
        answer = f"📌 Task '{task.title}' (ID: {task.id}) status moved to '{formatted_status}' successfully!"

        ai_chat.ai_answer = json.dumps({"status": "moved_status", "task_id": task.id})
        ai_chat.answer = answer
        db.commit()
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to move status: {str(e)}")


def handle_assign_task(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Assign task to a team member board-wise."""
    try:
        task_id = response_data.get("task_id") or response_data.get("id")
        task_title = response_data.get("task_title") or response_data.get("title")
        assignee_name = response_data.get("assignee") or response_data.get("assignee_id")
        
        task = find_task_by_title_or_id(db, user_id, task_id, task_title)

        if not task:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="Task not found. Please specify a valid task ID or title.")

        if not assignee_name:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="Assignee name is required. Please specify who to assign the task to.")

        target_user = None
        if isinstance(assignee_name, str) and assignee_name.strip().lower() in ["me", "myself", "current user", "i", "my"]:
            target_user = db.query(User).filter(User.id == user_id).first()
        else:
            search_str = str(assignee_name).strip().lower()
            all_users = db.query(User).all()
            for u in all_users:
                if search_str in u.email.lower() or search_str in (u.full_name or "").lower() or search_str in u.username.lower():
                    target_user = u
                    break

        if not target_user:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Team member '{assignee_name}' not found.")

        task.assignee_id = target_user.id
        db.commit()
        db.refresh(task)

        display_name = target_user.full_name or target_user.username or target_user.email
        answer = f"👤 Task '{task.title}' (ID: {task.id}) assigned to {display_name} successfully!"

        ai_chat.ai_answer = json.dumps({"status": "assigned", "task_id": task.id, "assignee_id": target_user.id})
        ai_chat.answer = answer
        db.commit()
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to assign task: {str(e)}")


def handle_create_task(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Prepare a task draft and prompt user for Yes/No creation confirmation."""
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        assignee_val = response_data.get("assignee") or response_data.get("assignee_id")
        resolved_assignee_id = None
        resolved_assignee_name = None

        if assignee_val:
            if isinstance(assignee_val, int):
                resolved_assignee_id = assignee_val
                u = db.query(User).filter(User.id == assignee_val).first()
                if u:
                    resolved_assignee_name = u.full_name or u.username or u.email
            elif isinstance(assignee_val, str):
                cleaned_a = assignee_val.strip().lower()
                if cleaned_a in ["me", "myself", "current user", "i", "my"]:
                    resolved_assignee_id = user_id
                    if current_user:
                        resolved_assignee_name = current_user.full_name or current_user.username or current_user.email
                else:
                    found = db.query(User).filter(
                        (User.username.ilike(f"%{cleaned_a}%")) | 
                        (User.full_name.ilike(f"%{cleaned_a}%")) |
                        (User.email.ilike(f"%{cleaned_a}%"))
                    ).first()
                    if found:
                        resolved_assignee_id = found.id
                        resolved_assignee_name = found.full_name or found.username or found.email

        task_title = response_data.get("title") or "New Task"
        raw_desc = response_data.get("description")
        if not raw_desc or raw_desc.strip().lower() in ["no description provided.", "no description provided", "none", "null", "n/a", "no description"]:
            task_desc = f"Implement necessary fixes and task requirements for '{task_title}'. Review design layout, code implementation, and verify functionality."
        else:
            task_desc = raw_desc.strip()

        fields = {
            "action_type": "create_task",
            "title": task_title,
            "description": task_desc,
            "board_name": response_data.get("board_name"),
            "priority": (response_data.get("priority") or "medium").lower(),
            "status": (response_data.get("status") or "todo").lower(),
            "tag": response_data.get("tag") or "Task",
            "assignee_id": resolved_assignee_id,
            "assignee_name": resolved_assignee_name,
        }

        ai_chat.ai_answer = json.dumps(fields)

        display_labels = {
            "title": "Title",
            "description": "Description",
            "status": "Status",
            "priority": "Priority",
            "board_name": "Board",
            "tag": "Tag",
            "assignee_name": "Assignee",
        }
        details = []
        for key, value in fields.items():
            if value is not None and key not in ["action_type", "assignee_id"]:
                label = display_labels.get(key, key)
                details.append(f"* **{label}**: {value}")

        details_str = "\n".join(details)

        answer = (
            f"I have prepared a draft of the task:\n\n"
            f"{details_str}\n\n"
            f"Would you like me to create this task? (Yes/No)"
        )

        ai_chat.answer = answer
        db.commit()
        db.refresh(ai_chat)

        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to create task: {str(e)}")


def handle_update_task(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Handle updating an existing task."""
    try:
        task_id = response_data.get("task_id") or response_data.get("id")
        if not task_id:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="Task ID is required for updating a task.")
        
        task = crud.get_task_by_id(db, task_id=int(task_id))
        if not task:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Task with ID {task_id} not found.")

        changes = []
        if response_data.get("title"):
            task.title = response_data["title"]
            changes.append(f"title → '{task.title}'")
        if response_data.get("description"):
            task.description = response_data["description"]
            changes.append("description updated")
        if response_data.get("priority"):
            task.priority = response_data["priority"]
            changes.append(f"priority → '{task.priority}'")
        if response_data.get("tag"):
            task.tag = response_data["tag"]
            changes.append(f"tag → '{task.tag}'")

        db.commit()
        db.refresh(task)
        
        changes_str = ", ".join(changes) if changes else "no fields changed"
        answer = f"Task updated successfully (ID: {task.id}, Title: {task.title}). Changes: {changes_str}"
        
        ai_chat.ai_answer = str(response_data)
        ai_chat.answer = answer
        ai_chat.task_id = task.id
        db.commit()

        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to update task: {str(e)}")


def handle_move_task(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Handle moving a task to a different board."""
    try:
        task_id = response_data.get("task_id") or response_data.get("id")
        board_name = response_data.get("board_name")

        if not task_id or not board_name:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer="Task ID and target board name are required.")

        task = crud.get_task_by_id(db, task_id=int(task_id))
        if not task:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Task with ID {task_id} not found.")

        board = board_crud.get_board_by_name(db, board_name, user_id)
        if not board:
            return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Board '{board_name}' not found.")

        task.board_id = board.id
        db.commit()
        db.refresh(task)

        answer = f"Task '{task.title}' (ID: {task.id}) has been moved to board '{board.name}' successfully!"

        ai_chat.ai_answer = str(response_data)
        ai_chat.answer = answer
        ai_chat.task_id = task.id
        db.commit()

        return FlowAIOut(question=ai_chat.question, is_static=False, answer=answer)
    except Exception as e:
        return FlowAIOut(question=ai_chat.question, is_static=False, answer=f"Failed to move task: {str(e)}")


def handle_other_request(db: Session, user_id: int, response_data: dict, ai_chat: AIChat) -> FlowAIOut:
    """Handle general AI questions."""
    answer = response_data.get("message") or "No response message provided."
    ai_chat.ai_answer = str(response_data)
    ai_chat.answer = answer
    db.commit()
    return FlowAIOut(question=ai_chat.question if hasattr(ai_chat, 'question') else "Question", is_static=False, answer=answer)
