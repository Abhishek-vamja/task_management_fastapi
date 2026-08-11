"""CRUD database operations for Organizations, Memberships, and Custom Ticket Keys."""

from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, delete
from apps.organizations.models import Organization, OrganizationMember, OrganizationInvite
from apps.boards.models import Board, BoardMember
from apps.tasks.models import Task
from apps.users.models import User


def get_organization_by_id(db: Session, org_id: int) -> Organization | None:
    """Retrieve an Organization by its primary key ID."""
    return db.get(Organization, org_id)


def get_organization_by_key(db: Session, key: str) -> Organization | None:
    """Retrieve an Organization by its uppercase key prefix (e.g. 'FAA')."""
    clean_key = key.strip().upper()
    return db.scalars(select(Organization).where(Organization.key == clean_key)).first()


def get_user_organizations(db: Session, user_id: int) -> list[Organization]:
    """Retrieve all distinct Organizations a user belongs to."""
    return list(
        db.scalars(
            select(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user_id)
            .distinct()
            .order_by(Organization.created_at.desc())
        ).all()
    )


def get_organization_members(db: Session, organization_id: int) -> list[OrganizationMember]:
    """Retrieve all unique members of an Organization with User details."""
    raw_members = list(
        db.scalars(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(OrganizationMember.joined_at.asc())
        ).all()
    )
    seen_users = set()
    unique_members = []
    for m in raw_members:
        if m.user_id not in seen_users:
            seen_users.add(m.user_id)
            user = db.get(User, m.user_id)
            m.username = user.username if user else None
            m.email = user.email if user else None
            m.full_name = user.full_name if user else None
            unique_members.append(m)
    return unique_members


def create_organization(db: Session, name: str, key: str, owner_id: int) -> Organization:
    """Create a new Organization and automatically add the owner as an owner member."""
    clean_key = key.strip().upper()
    
    # Check if key is taken
    existing = get_organization_by_key(db, clean_key)
    if existing:
        raise ValueError(f"Organization key '{clean_key}' is already in use. Please choose a different prefix.")

    org = Organization(
        name=name.strip(),
        key=clean_key,
        owner_id=owner_id,
        counter=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Add owner membership
    member = OrganizationMember(
        organization_id=org.id,
        user_id=owner_id,
        role="owner"
    )
    db.add(member)
    db.commit()

    return org


def generate_next_ticket_key(db: Session, organization_id: int) -> tuple[str, int]:
    """Atomically increment organization task counter and return (ticket_key, task_number). e.g. ('FAA-1', 1)."""
    org = get_organization_by_id(db, organization_id)
    if not org:
        raise ValueError(f"Organization ID {organization_id} not found.")

    org.counter += 1
    db.commit()
    db.refresh(org)

    ticket_key = f"{org.key}-{org.counter}"
    return ticket_key, org.counter


def migrate_user_existing_data(db: Session, user_id: int, name: str, key: str) -> Organization:
    """Migrate existing boards & tasks for a user by creating their primary Organization and assigning FAA-1 keys."""
    # 1. Create Organization
    org = create_organization(db, name=name, key=key, owner_id=user_id)

    # 2. Link all existing boards created by or belonging to user that don't have an org_id
    user_boards = list(db.scalars(
        select(Board)
        .join(BoardMember, Board.id == BoardMember.board_id)
        .where(BoardMember.user_id == user_id, Board.organization_id.is_(None))
    ).all())

    for b in user_boards:
        b.organization_id = org.id

    db.commit()

    # 3. Fetch all tasks created by or assigned to user without an organization_id
    unlinked_tasks = list(db.scalars(
        select(Task).where(
            (Task.user_id == user_id) | (Task.assignee_id == user_id),
            Task.organization_id.is_(None)
        ).order_by(Task.id.asc())
    ).all())

    for task in unlinked_tasks:
        task.organization_id = org.id
        ticket_key, task_num = generate_next_ticket_key(db, org.id)
        task.ticket_key = ticket_key
        task.task_number = task_num

    db.commit()

    return org


def remove_organization_member(db: Session, organization_id: int, target_user_id: int) -> bool:
    """Remove a user from an Organization and automatically set assignee_id = NULL on all their assigned tasks in that Org."""
    # 1. Delete membership
    db.execute(
        delete(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == target_user_id
        )
    )

    # 2. Automatically set assignee_id = NULL on tasks assigned to target_user_id within this organization
    db.execute(
        update(Task)
        .where(
            Task.organization_id == organization_id,
            Task.assignee_id == target_user_id
        )
        .values(assignee_id=None)
    )

    db.commit()
    return True


def invite_user_to_org(db: Session, organization_id: int, email: str, sender_id: int, role: str = "member") -> OrganizationInvite:
    """Create an invitation token for joining an Organization."""
    token = f"org_inv_{uuid4().hex}"
    invite = OrganizationInvite(
        organization_id=organization_id,
        email=email.strip().lower(),
        token=token,
        sender_id=sender_id,
        role=role,
        status="pending"
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def accept_org_invite(db: Session, token: str, user_id: int) -> Organization:
    """Accept an Organization invitation using token."""
    invite = db.scalars(
        select(OrganizationInvite).where(
            OrganizationInvite.token == token,
            OrganizationInvite.status == "pending"
        )
    ).first()

    if not invite:
        raise ValueError("Invalid or expired invitation token.")

    org = get_organization_by_id(db, invite.organization_id)
    if not org:
        raise ValueError("Organization no longer exists.")

    # Add user to organization members if not already
    existing_mem = db.scalars(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id
        )
    ).first()

    if not existing_mem:
        mem = OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role=invite.role
        )
        db.add(mem)

    invite.status = "accepted"
    db.commit()
    return org
