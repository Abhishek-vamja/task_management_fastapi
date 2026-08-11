from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from apps.database import get_db
from apps.auth.dependencies import get_current_user
from apps.users.models import User
from apps.users.crud import get_user_by_email
from apps.users.schemas import UserOut
from apps.tasks.schemas import TaskOut
from apps.boards import crud
from apps.boards.schemas import (
    BoardCreate, BoardOut, BoardMemberOut, InvitationCreate, InvitationOut
)
from services.bravo import send_invitation_email

router = APIRouter(
    tags=["Boards & Members"]
)


# --- Boards Endpoints ---

@router.post("/boards/", response_model=BoardOut, status_code=status.HTTP_201_CREATED)
def create_new_board(
    board_in: BoardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new board and auto-add creator as 'manager'."""
    return crud.create_board(db, board_data=board_in, owner_id=current_user.id)


from fastapi import APIRouter, Depends, Query, Header, status, HTTPException

@router.get("/boards/", response_model=list[BoardOut])
def read_my_boards(
    organization_id: int | None = Query(None),
    x_organization_id: int | None = Header(None, alias="X-Organization-Id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all boards the current user has access to, filtered by organization_id."""
    target_org_id = organization_id or x_organization_id
    return crud.get_user_boards(db, user_id=current_user.id, organization_id=target_org_id)


@router.get("/boards/{board_id}", response_model=BoardOut)
def read_board_by_id(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch board details by ID. Verified access first."""
    membership = crud.get_board_member(db, board_id=board_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board."
        )
    board = crud.get_board_by_id(db, board_id=board_id)
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found.")
    return board


@router.get("/boards/{board_id}/tasks", response_model=list[TaskOut])
def read_board_tasks(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all tasks for a board. Verified access first."""
    membership = crud.get_board_member(db, board_id=board_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board's tasks."
        )
    return crud.get_board_tasks(db, board_id=board_id)


@router.put("/boards/{board_id}/columns", response_model=BoardOut)
def update_columns(
    board_id: int,
    columns: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update custom status columns of a board. Restricted to managers & leads."""
    membership = crud.get_board_member(db, board_id=board_id, user_id=current_user.id)
    if not membership or membership.role not in ("manager", "lead"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board managers and team leads can modify columns."
        )
    
    board = crud.get_board_by_id(db, board_id=board_id)
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found.")
        
    return crud.update_board_columns(db, board=board, columns=columns)


# --- Members & Invitations Endpoints ---

@router.post("/boards/{board_id}/invite")
def invite_or_add_member(
    board_id: int,
    invite_in: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite or directly add a team member to the board. Restricted to managers & leads."""
    # Check permissions (any member of the board can invite)
    membership = crud.get_board_member(db, board_id=board_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this board to invite new team members."
        )

    board = crud.get_board_by_id(db, board_id=board_id)
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found.")

    # 1. Check if user already exists in system by email
    existing_user = get_user_by_email(db, email=invite_in.email)
    if existing_user:
        # Check if they are already in the board
        existing_membership = crud.get_board_member(db, board_id=board_id, user_id=existing_user.id)
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this board."
            )
        
        # Add directly
        new_member = crud.add_board_member(db, board_id=board_id, user_id=existing_user.id, role=invite_in.role)
        return {
            "status": "added_directly",
            "message": f"User {invite_in.email} added directly to board.",
            "member_id": new_member.id
        }

    # 2. User does not exist, send invitation
    invitation = crud.create_invitation(db, board_id=board_id, invite_data=invite_in, sender_id=current_user.id)
    
    # Send email containing the invite link
    invite_link = f"http://localhost:5173/accept-invite?token={invitation.token}"
    inviter_name = current_user.full_name or current_user.username
    send_invitation_email(
        email=invitation.email,
        inviter_name=inviter_name,
        board_name=board.name,
        invite_link=invite_link
    )

    return {
        "status": "invited",
        "message": f"Invitation email sent to {invite_in.email}.",
        "invitation_id": invitation.id
    }


@router.post("/auth/invitations/accept/{token}")
def accept_board_invite(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a pending invitation for the currently logged-in user."""
    invitation = crud.get_invitation_by_token(db, token=token)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")

    if invitation.status == "accepted":
        return {
            "message": "Invitation already accepted.",
            "board_id": invitation.board_id,
            "role": invitation.role
        }

    member = crud.accept_invitation(db, invitation=invitation, user=current_user)
    return {
        "message": "Invitation accepted successfully.",
        "board_id": member.board_id,
        "role": member.role
    }


@router.get("/boards/{board_id}/members", response_model=list[BoardMemberOut])
def read_board_members(
    board_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch list of board members. Restrict to board members."""
    membership = crud.get_board_member(db, board_id=board_id, user_id=current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board's member list."
        )
    
    # Query members and join with User to serialize
    members = crud.get_board_members(db, board_id=board_id)
    # SQLAlchemy relationship will automatically populate member.user if configured, 
    # but let's make sure User is mapped dynamically.
    # To be safe, let's load users explicitly or ensure relations work.
    for m in members:
        # Explicitly fetch user and attach to the temporary object for schema serialization
        m.user = db.query(User).filter(User.id == m.user_id).first()
        
    return members
