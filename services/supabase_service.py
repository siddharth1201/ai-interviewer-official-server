from supabase import create_client, Client
from typing import Dict, List, Optional, Any
import os
from dataclasses import dataclass


@dataclass
class InterviewerGeminiResponse:
    """Data class for API responses"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    count: Optional[int] = None


class InterviewerGeminiService:
    """Service class for managing interviewer_gemini table operations"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize the Supabase client
        
        Args:
            supabase_url (str): Your Supabase project URL
            supabase_key (str): Your Supabase anon key
        """
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            self.table_name = "interviewer_gemini"
        except Exception as e:
            raise Exception(f"Failed to initialize Supabase client: {str(e)}")
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> InterviewerGeminiResponse:
        """
        Get all records from interviewer_gemini table
        
        Args:
            limit (Optional[int]): Limit the number of records returned
            offset (Optional[int]): Number of records to skip
            
        Returns:
            InterviewerGeminiResponse: Response object with data or error
        """
        try:
            query = self.supabase.table(self.table_name).select("*")
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            response = query.execute()
            
            return InterviewerGeminiResponse(
                success=True,
                data=response.data,
                count=len(response.data) if response.data else 0
            )
            
        except Exception as e:
            return InterviewerGeminiResponse(
                success=False,
                error=f"Failed to fetch all records: {str(e)}"
            )
    
    def get_by_id(self, record_id: Any) -> InterviewerGeminiResponse:
        """
        Get a single record by ID from interviewer_gemini table
        
        Args:
            record_id (Any): The ID of the record to fetch
            
        Returns:
            InterviewerGeminiResponse: Response object with data or error
        """
        try:
            response = self.supabase.table(self.table_name).select("*").eq("id", record_id).execute()
            
            if response.data and len(response.data) > 0:
                return InterviewerGeminiResponse(
                    success=True,
                    data=response.data[0],  # Return single record
                    count=1
                )
            else:
                return InterviewerGeminiResponse(
                    success=False,
                    error=f"No record found with ID: {record_id}"
                )
                
        except Exception as e:
            return InterviewerGeminiResponse(
                success=False,
                error=f"Failed to fetch record with ID {record_id}: {str(e)}"
            )
    
    def get_with_filters(self, filters: Dict[str, Any]) -> InterviewerGeminiResponse:
        """
        Get records with custom filters
        
        Args:
            filters (Dict[str, Any]): Dictionary of column:value pairs to filter by
            
        Returns:
            InterviewerGeminiResponse: Response object with data or error
        """
        try:
            query = self.supabase.table(self.table_name).select("*")
            
            # Apply filters
            for column, value in filters.items():
                query = query.eq(column, value)
            
            response = query.execute()
            
            return InterviewerGeminiResponse(
                success=True,
                data=response.data,
                count=len(response.data) if response.data else 0
            )
            
        except Exception as e:
            return InterviewerGeminiResponse(
                success=False,
                error=f"Failed to fetch records with filters: {str(e)}"
            )


# Example usage
if __name__ == "__main__":
    # Initialize the service
    # SUPABASE_URL = "YOUR_SUPABASE_URL"
    # SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
    
    # Or load from environment variables
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    try:
        service = InterviewerGeminiService(SUPABASE_URL, SUPABASE_KEY)
        
        # Get all records
        print("Fetching all records...")
        all_records = service.get_all()
        if all_records.success:
            print(f"Found {all_records.count} records")
            print(all_records.data)
        else:
            print(f"Error: {all_records.error}")
        
        # Get record by ID
        print("\nFetching record by ID...")
        record_by_id = service.get_by_id(945)  # Replace with actual ID
        if record_by_id.success:
            print("Record found:")
            print(record_by_id.data)
        else:
            print(f"Error: {record_by_id.error}")
        
        # Get with custom filters
        print("\nFetching with filters...")
        filtered_records = service.get_with_filters({"status": "active"})
        if filtered_records.success:
            print(f"Found {filtered_records.count} active records")
            print(filtered_records.data)
        else:
            print(f"Error: {filtered_records.error}")
            
    except Exception as e:
        print(f"Failed to initialize service: {e}")