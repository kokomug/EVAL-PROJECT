import streamlit as st
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Union

load_dotenv()

# Initialize Supabase client
@st.cache_resource
def get_supabase_client() -> Client:
    supabase_url = os.environ.get("SUPABASE_URL", "https://xolzhwksoafumenbhugs.supabase.co")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        st.error("Supabase URL or Key not found. Please add to .env file.")
        return None
    
    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Error initializing Supabase client: {e}")
        return None

# --- AUTHENTICATION FUNCTIONS ---

def signup_user(email: str, password: str, role: str = "student") -> dict:
    """Sign up a new user with Supabase and set their role."""
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client initialization failed"}
    
    try:
        # Register user
        auth_response = client.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if auth_response.user and auth_response.user.id:
            # Update the role in profiles table
            # Ensure the 'profiles' table and 'role' column exist
            update_data = {"role": role, "email": email} # Also store email in profile
            _, error = client.table('profiles').update(update_data).eq('id', auth_response.user.id).execute()
            if error and isinstance(error, tuple) and error[1].get('code') == '42P01': # table "profiles" does not exist
                 # if trigger didn't work or was not set, insert profile
                _, error_insert = client.table('profiles').insert({
                    "id": auth_response.user.id,
                    "email": email,
                    "role": role
                }).execute()
                if error_insert:
                     return {"error": f"Failed to create profile: {error_insert[1].get('message') if isinstance(error_insert, tuple) else error_insert}"}

            elif error:
                 return {"error": f"Failed to update role: {error[1].get('message') if isinstance(error, tuple) else error}"}


            return {"success": True, "user": auth_response.user, "role": role}
        elif auth_response.user and not auth_response.user.id and auth_response.user.aud == 'authenticated':
            # User might exist but is not confirmed. This case might need handling for email confirmation.
            # For now, let's assume auto-confirmation or proceed as if signup was successful for the profile part.
            # Attempt to get user by email if ID is missing initially for an existing unconfirmed user.
            get_user_response = client.auth.admin.get_user_by_id(auth_response.user.id) # This needs admin rights usually.
            # This part is complex, better to rely on the trigger or ensure confirmation is handled.
            # For now, we assume the trigger handles profile creation.
            # If the user is returned but no session, it might mean email confirmation is pending.
            return {"error": "User might exist or email confirmation is pending."}

        else:
            error_message = "User registration failed"
            if auth_response and hasattr(auth_response, 'message'):
                error_message += f": {auth_response.message}"
            elif auth_response and hasattr(auth_response, 'error_description'):
                 error_message += f": {auth_response.error_description}"

            return {"error": error_message, "details": auth_response}
    except Exception as e:
        return {"error": str(e)}


def signin_user(email: str, password: str) -> dict:
    """Sign in an existing user with Supabase."""
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client initialization failed"}
    
    try:
        auth_response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user:
            # Get user role from profiles
            profile_query = client.table('profiles').select('role').eq('id', auth_response.user.id).execute()
            
            if profile_query.data and len(profile_query.data) > 0:
                role = profile_query.data[0].get('role', 'student')
                return {"success": True, "user": auth_response.user, "session": auth_response.session, "role": role}
            else:
                # Fallback or if profile is missing (should not happen with trigger)
                return {"success": True, "user": auth_response.user, "session": auth_response.session, "role": "student"} # Default to student
        else:
            error_message = "Login failed"
            if auth_response and hasattr(auth_response, 'message'):
                error_message += f": {auth_response.message}"
            elif auth_response and hasattr(auth_response, 'error_description'):
                 error_message += f": {auth_response.error_description}"
            return {"error": error_message, "details": auth_response}
    except Exception as e:
        # Catch Supabase spezifische AuthApiError
        if "Invalid login credentials" in str(e):
            return {"error": "Invalid email or password."}
        return {"error": str(e)}

def signout_user() -> dict:
    """Sign out the current user."""
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client initialization failed"}
    
    try:
        client.auth.sign_out()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def get_current_user() -> dict:
    """Get the current logged in user from session."""
    client = get_supabase_client()
    if not client:
        return {"error": "Supabase client initialization failed"}
    
    try:
        # Try to get session first
        session = client.auth.get_session()
        if session and session.user:
            user = session.user
            # Get user role from profiles
            profile_query = client.table('profiles').select('role').eq('id', user.id).execute()
            if profile_query.data and len(profile_query.data) > 0:
                role = profile_query.data[0].get('role', 'student')
                return {"success": True, "user": user, "role": role}
            else:
                 # This case should ideally not happen if the profile trigger works.
                return {"success": True, "user": user, "role": "student"} # Default to student if profile somehow missing
        else: # If no session, try get_user (might work if token is stored differently by Streamlit)
            user_response = client.auth.get_user()
            if user_response and user_response.user:
                user = user_response.user
                profile_query = client.table('profiles').select('role').eq('id', user.id).execute()
                if profile_query.data and len(profile_query.data) > 0:
                    role = profile_query.data[0].get('role', 'student')
                    return {"success": True, "user": user, "role": role}
                else:
                    return {"success": True, "user": user, "role": "student"} 
            return {"error": "No user is logged in or session expired"}
            
    except Exception as e:
        return {"error": f"Error fetching user: {str(e)}"}

def get_user_id() -> Union[str, None]:
    user_info = get_current_user()
    if user_info.get("success") and user_info.get("user"):
        return user_info["user"].id
    return None

def get_user_role() -> Union[str, None]:
    user_info = get_current_user()
    if user_info.get("success"):
        return user_info.get("role")
    return None 