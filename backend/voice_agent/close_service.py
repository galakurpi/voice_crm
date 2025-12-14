import os
import httpx
import base64
import json

# Get API key from environment
CLOSE_API_KEY = os.getenv('CLOSE_API_KEY')
CLOSE_API_BASE = 'https://api.close.com/api/v1'

def get_auth_header():
    """Constructs the Basic Auth header for Close.com API."""
    if not CLOSE_API_KEY:
        # In production, you might want to log a warning or error here
        # For now, we'll raise an error to ensure it's configured
        raise ValueError("CLOSE_API_KEY not found in environment variables.")
    
    # Basic Auth: api_key as username, empty password (indicated by the colon)
    credentials = f"{CLOSE_API_KEY}:"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        'Authorization': f'Basic {encoded}',
        'Content-Type': 'application/json'
    }

async def search_leads(query: str, limit: int = 10000) -> str:
    """
    Searches for leads in Close.com by name or keyword.
    Returns a formatted string of results.
    """
    url = f"{CLOSE_API_BASE}/lead/"
    # Fetching only essential fields to keep the context size small
    params = {
        'query': query,
        '_fields': 'id,display_name,status_label,contacts,opportunities',
        'limit': limit
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=get_auth_header(), params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for lead in data.get('data', []):
                # Extract contact names
                contact_names = [
                    c.get('display_name', 'Unknown') 
                    for c in lead.get('contacts', [])
                ]
                
                # Extract opportunity info
                opps = lead.get('opportunities', [])
                opp_info = ", ".join([f"{o.get('status_label', 'Unknown')} (${o.get('value_formatted', '0')})" for o in opps])
                
                # Format the lead info
                info = (
                    f"ID: {lead.get('id')}\n"
                    f"Name: {lead.get('display_name')}\n"
                    f"Status: {lead.get('status_label')}\n"
                    f"Contacts: {', '.join(contact_names)}\n"
                    f"Opportunities: {opp_info if opp_info else 'None'}"
                )
                results.append(info)
            
            if not results:
                return "No leads found matching that query."
                
            return "\n---\n".join(results)
            
    except httpx.HTTPStatusError as e:
        return f"Error searching leads: {e.response.text}"
    except Exception as e:
        return f"Error searching leads: {str(e)}"

async def get_lead_details(lead_id: str) -> str:
    """
    Get full details for a specific lead.
    """
    url = f"{CLOSE_API_BASE}/lead/{lead_id}/"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=get_auth_header())
            response.raise_for_status()
            lead = response.json()
            
            # Format the lead info in a readable way
            info = (
                f"ID: {lead.get('id')}\n"
                f"Name: {lead.get('display_name')}\n"
                f"Status: {lead.get('status_label')}\n"
                f"Description: {lead.get('description', 'N/A')}\n"
                f"URL: {lead.get('url', 'N/A')}\n"
            )
            return info
            
    except httpx.HTTPStatusError as e:
        return f"Error getting lead details: {e.response.text}"
    except Exception as e:
        return f"Error getting lead details: {str(e)}"

async def create_lead(company_name: str, contact_name: str = None, email: str = None) -> str:
    """
    Creates a new lead with an optional contact.
    """
    url = f"{CLOSE_API_BASE}/lead/"
    
    payload = {
        'name': company_name,
        'contacts': []
    }
    
    if contact_name or email:
        contact = {}
        if contact_name:
            contact['name'] = contact_name
        if email:
            contact['emails'] = [{'email': email, 'type': 'office'}]
        payload['contacts'].append(contact)
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=get_auth_header(), json=payload)
            response.raise_for_status()
            data = response.json()
            return f"Lead created successfully. ID: {data.get('id')}"
            
    except httpx.HTTPStatusError as e:
        return f"Error creating lead: {e.response.text}"
    except Exception as e:
        return f"Error creating lead: {str(e)}"

async def update_lead_description(lead_id: str, description: str) -> str:
    """Update the description/about field of a lead."""
    url = f"{CLOSE_API_BASE}/lead/{lead_id}/"
    payload = {'description': description}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=get_auth_header(), json=payload)
            response.raise_for_status()
            return "Lead description updated."
    except Exception as e:
        return f"Error updating lead: {str(e)}"

async def add_lead_note(lead_id: str, note_text: str) -> str:
    """
    Adds a note to a specific lead in Close.com.
    """
    url = f"{CLOSE_API_BASE}/activity/note/"
    payload = {
        'lead_id': lead_id,
        'note': note_text
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=get_auth_header(), json=payload)
            response.raise_for_status()
            return "Note added successfully to the lead."
            
    except httpx.HTTPStatusError as e:
        return f"Error adding note: {e.response.text}"
    except Exception as e:
        return f"Error adding note: {str(e)}"

async def get_lead_notes(lead_id: str) -> str:
    """
    Get all notes for a specific lead.
    """
    url = f"{CLOSE_API_BASE}/activity/note/"
    params = {
        'lead_id': lead_id,
        '_fields': 'id,note,date_created,user_name',
        '_order_by': '-date_created'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=get_auth_header(), params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for note in data.get('data', []):
                info = (
                    f"Note ID: {note.get('id')}\n"
                    f"Date: {note.get('date_created')}\n"
                    f"Author: {note.get('user_name', 'Unknown')}\n"
                    f"Content: {note.get('note')}"
                )
                results.append(info)
            
            if not results:
                return "No notes found for this lead."
                
            return "\n---\n".join(results)
            
    except httpx.HTTPStatusError as e:
        return f"Error getting notes: {e.response.text}"
    except Exception as e:
        return f"Error getting notes: {str(e)}"

async def update_note(note_id: str, new_text: str) -> str:
    """
    Updates the content of a specific note.
    """
    url = f"{CLOSE_API_BASE}/activity/note/{note_id}/"
    payload = {
        'note': new_text
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=get_auth_header(), json=payload)
            response.raise_for_status()
            return "Note updated successfully."
            
    except httpx.HTTPStatusError as e:
        return f"Error updating note: {e.response.text}"
    except Exception as e:
        return f"Error updating note: {str(e)}"

async def create_opportunity(lead_id: str, note: str, value: int, status: str = "Active") -> str:
    """
    Creates a new opportunity for a lead.
    """
    url = f"{CLOSE_API_BASE}/opportunity/"
    payload = {
        'lead_id': lead_id,
        'note': note,
        'value': value,
        'value_period': 'one_time', # Simplification
        'status': status 
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=get_auth_header(), json=payload)
            response.raise_for_status()
            data = response.json()
            return f"Opportunity created. ID: {data.get('id')}"
            
    except httpx.HTTPStatusError as e:
        return f"Error creating opportunity: {e.response.text}"
    except Exception as e:
        return f"Error creating opportunity: {str(e)}"

async def get_opportunities(limit: int = 10000, sort_by: str = '-value', status_label: str = None) -> str:
    """
    Get a list of opportunities, sorted by value by default.
    Optionally filter by status label.
    """
    url = f"{CLOSE_API_BASE}/opportunity/"
    
    # If filtering client-side, fetch maximum allowed per page to find matches
    api_limit = limit
    if status_label:
        api_limit = 200
    
    params = {
        '_limit': api_limit,
        '_order_by': sort_by,
        '_fields': 'id,note,value,value_formatted,status_label,lead_name'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=get_auth_header(), params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for opp in data.get('data', []):
                # Apply optional status filtering
                if status_label:
                    # Case-insensitive partial match for user convenience
                    if status_label.lower() not in opp.get('status_label', '').lower():
                        continue

                info = (
                    f"Opp ID: {opp.get('id')}\n"
                    f"Lead: {opp.get('lead_name', 'Unknown')}\n"
                    f"Value: {opp.get('value_formatted', '$0')}\n"
                    f"Status: {opp.get('status_label')}\n"
                    f"Note: {opp.get('note', 'No details')}"
                )
                results.append(info)
                
                # Stop once we have enough matches
                if len(results) >= limit:
                    break
            
            if not results:
                return f"No opportunities found matching status '{status_label}'." if status_label else "No opportunities found."
                
            return "\n---\n".join(results)
            
    except httpx.HTTPStatusError as e:
        return f"Error getting opportunities: {e.response.text}"
    except Exception as e:
        return f"Error getting opportunities: {str(e)}"

async def list_leads(limit: int = 10000, query: str = '') -> str:
    """
    List multiple leads, optionally filtered by a query.
    Similar to search_leads but focused on listing for 'all' requests.
    """
    return await search_leads(query if query else '*', limit=limit)
