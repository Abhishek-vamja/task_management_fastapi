"""API endpoints for Organization Workspaces, Custom Ticket Keys, and Memberships."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from apps.database import get_db
from apps.auth.dependencies import get_current_user
from apps.users.models import User
from apps.organizations import crud as org_crud
from apps.organizations.schemas import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationMemberOut,
    OrganizationInviteCreate,
    OrganizationInviteOut,
    OrganizationMigrateSetup,
)

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Organization workspace with custom key prefix."""
    try:
        return org_crud.create_organization(
            db=db,
            name=org_in.name,
            key=org_in.key,
            owner_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=list[OrganizationOut], status_code=status.HTTP_200_OK)
def list_user_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all Organizations authenticated user belongs to."""
    return org_crud.get_user_organizations(db=db, user_id=current_user.id)


@router.get("/{org_id}/members", response_model=list[OrganizationMemberOut], status_code=status.HTTP_200_OK)
def list_organization_members(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all members belonging to an Organization."""
    org = org_crud.get_organization_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return org_crud.get_organization_members(db=db, organization_id=org_id)


@router.post("/migrate-setup", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def migrate_setup_organization(
    org_in: OrganizationMigrateSetup,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mandatory setup endpoint for existing users logging in without an Organization.
    Creates primary Org and automatically links existing boards and assigns FAA-1 ticket keys.
    """
    try:
        return org_crud.migrate_user_existing_data(
            db=db,
            user_id=current_user.id,
            name=org_in.name,
            key=org_in.key
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{org_id}/invite", response_model=OrganizationInviteOut, status_code=status.HTTP_201_CREATED)
def invite_user_to_organization(
    org_id: int,
    invite_in: OrganizationInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite a team member to join an Organization."""
    org = org_crud.get_organization_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    if org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Organization owner can invite members."
        )
    
    invite = org_crud.invite_user_to_org(
        db=db,
        organization_id=org_id,
        email=invite_in.email,
        sender_id=current_user.id,
        role=invite_in.role
    )

    # Dispatch transactional invitation email via Brevo / email service
    from services.bravo import send_organization_invitation_email
    inviter_name = current_user.full_name or current_user.username
    invite_link = f"http://localhost:5173/accept-invite?token={invite.token}"
    send_organization_invitation_email(
        email=invite.email,
        inviter_name=inviter_name,
        org_name=org.name,
        org_key=org.key,
        invite_link=invite_link
    )

    return invite


@router.post("/accept-invite/{token}", response_model=OrganizationOut, status_code=status.HTTP_200_OK)
def accept_organization_invite(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept an invitation to join an Organization via token."""
    try:
        return org_crud.accept_org_invite(db=db, token=token, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member_from_organization(
    org_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from an Organization and automatically set assignee_id = NULL for their assigned tasks."""
    org = org_crud.get_organization_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    if org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Organization owner can remove members."
        )

    org_crud.remove_organization_member(db=db, organization_id=org_id, target_user_id=user_id)
    return None
