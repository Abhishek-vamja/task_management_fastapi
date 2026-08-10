import secrets
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from apps.boards.models import Board, BoardMember, Invitation
from apps.boards.schemas import BoardCreate, InvitationCreate
from apps.users.models import User
from apps.tasks.models import Task


# --- Board CRUD ---

def create_board(db: Session, board_data: BoardCreate, owner_id: int) -> Board:
    """Create a new Kanban board and automatically add the owner as 'manager'."""
    db_board = Board(
        name=board_data.name,
        description=board_data.description,
        type=board_data.type,
        privacy=board_data.privacy,
        accent_color=board_data.accent_color,
        icon=board_data.icon,
        columns=board_data.columns,
        owner_id=owner_id
    )
    db.add(db_board)
    db.commit()
    db.refresh(db_board)

    # Automatically add owner as a member with 'manager' role
    add_board_member(db, board_id=db_board.id, user_id=owner_id, role="manager")
    
    return db_board


def get_board_by_id(db: Session, board_id: int) -> Board | None:
    """Fetch board by primary key ID."""
    return db.scalars(select(Board).where(Board.id == board_id)).first()


def get_user_boards(db: Session, user_id: int) -> list[Board]:
    """Fetch all boards a user is a member of."""
    query = select(Board).join(BoardMember).where(BoardMember.user_id == user_id)
    return list(db.scalars(query).all())


def get_board_by_name(db: Session, name: str, user_id: int) -> Board | None:
    """Intelligently match a board by name among boards the user is a member of.

    Tries exact match first, then uses fuzzy sequence matching to pick the best matching board.
    """
    from difflib import SequenceMatcher

    user_boards = get_user_boards(db, user_id)
    if not user_boards:
        return None

    clean_query = name.strip().lower()

    # 1. Exact case-insensitive match
    for board in user_boards:
        if board.name.lower() == clean_query:
            return board

    # 2. Fuzzy sequence similarity matching
    best_board = None
    best_score = -1.0

    for board in user_boards:
        b_name_lower = board.name.lower()
        
        # Sequence similarity ratio
        ratio = SequenceMatcher(None, clean_query, b_name_lower).ratio()
        
        # Substring / partial match ratio
        partial_ratio = 0.0
        if len(clean_query) > len(b_name_lower):
            for i in range(len(clean_query) - len(b_name_lower) + 1):
                sub = clean_query[i:i + len(b_name_lower)]
                r = SequenceMatcher(None, sub, b_name_lower).ratio()
                if r > partial_ratio:
                    partial_ratio = r
        else:
            partial_ratio = ratio

        score = max(ratio, partial_ratio) * (1.0 + 0.05 * len(b_name_lower))

        if score > best_score:
            best_score = score
            best_board = board

    return best_board


def get_board_tasks(db: Session, board_id: int) -> list[Task]:
    """Fetch all tasks for a board, ordered by position."""
    query = select(Task).where(Task.board_id == board_id).order_by(Task.position.asc())
    return list(db.scalars(query).all())


def update_board_columns(db: Session, board: Board, columns: list[str]) -> Board:
    """Update custom status columns of a board."""
    board.columns = columns
    db.commit()
    db.refresh(board)
    return board


# --- Board Member & Invitation CRUD ---

def get_board_member(db: Session, board_id: int, user_id: int) -> BoardMember | None:
    """Fetch board membership details for a specific user."""
    return db.scalars(
        select(BoardMember).where(BoardMember.board_id == board_id, BoardMember.user_id == user_id)
    ).first()


def add_board_member(db: Session, board_id: int, user_id: int, role: str) -> BoardMember:
    """Directly insert a user as a member of a board."""
    member = BoardMember(board_id=board_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def get_board_members(db: Session, board_id: int) -> list[BoardMember]:
    """Fetch all members of a board including their User profiles."""
    query = select(BoardMember).where(BoardMember.board_id == board_id)
    return list(db.scalars(query).all())


def create_invitation(db: Session, board_id: int, invite_data: InvitationCreate, sender_id: int) -> Invitation:
    """Generate a pending board invitation with a secure token."""
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        email=invite_data.email,
        board_id=board_id,
        role=invite_data.role,
        personal_message=invite_data.personal_message,
        token=token,
        status="pending",
        sender_id=sender_id
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def get_invitation_by_token(db: Session, token: str) -> Invitation | None:
    """Fetch invitation details by secure token."""
    return db.scalars(select(Invitation).where(Invitation.token == token)).first()


def accept_invitation(db: Session, invitation: Invitation, user: User) -> BoardMember:
    """Process acceptance of a pending invitation, creating board membership."""
    invitation.status = "accepted"
    
    # Check if they are already a member
    existing_member = get_board_member(db, board_id=invitation.board_id, user_id=user.id)
    if existing_member:
        db.commit()
        return existing_member

    member = BoardMember(
        board_id=invitation.board_id,
        user_id=user.id,
        role=invitation.role
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def process_pending_invitations_for_user(db: Session, user: User, invite_token: str | None = None) -> list[BoardMember]:
    """Auto-accept pending invitations for a user by token or matching email address."""
    accepted = []

    # 1. Accept specific invitation token if provided
    if invite_token and invite_token.strip():
        invitation = get_invitation_by_token(db, token=invite_token.strip())
        if invitation and invitation.status == "pending":
            member = accept_invitation(db, invitation, user)
            accepted.append(member)

    # 2. Accept any pending invitations matching user's email address
    query = select(Invitation).where(
        Invitation.status == "pending",
        func.lower(Invitation.email) == user.email.lower()
    )
    pending_invites = list(db.scalars(query).all())
    for invitation in pending_invites:
        member = accept_invitation(db, invitation, user)
        accepted.append(member)

    return accepted
