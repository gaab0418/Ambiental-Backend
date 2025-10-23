"""
File Upload Utility
Handles file uploads for profiles, logos, and documents
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from PIL import Image
import shutil


class FileUploadUtils:
    """Utility class for handling file uploads"""
    
    # Allowed file extensions
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'}
    
    # Max file sizes (in bytes)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Upload directories
    UPLOAD_DIR = Path("uploads")
    PROFILE_DIR = UPLOAD_DIR / "profiles"
    LOGO_DIR = UPLOAD_DIR / "logos"
    DOCUMENT_DIR = UPLOAD_DIR / "documents"
    
    @classmethod
    def _ensure_upload_dirs(cls):
        """Ensure upload directories exist"""
        cls.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGO_DIR.mkdir(parents=True, exist_ok=True)
        cls.DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _get_file_extension(cls, filename: str) -> str:
        """Get file extension in lowercase"""
        return Path(filename).suffix.lower()
    
    @classmethod
    def _generate_unique_filename(cls, original_filename: str) -> str:
        """Generate a unique filename preserving extension"""
        ext = cls._get_file_extension(original_filename)
        unique_name = f"{uuid.uuid4()}{ext}"
        return unique_name
    
    @classmethod
    async def save_profile_image(
        cls,
        file: UploadFile,
        max_size: Tuple[int, int] = (800, 800)
    ) -> str:
        """
        Save and optimize profile image
        
        Args:
            file: Uploaded file
            max_size: Maximum dimensions (width, height)
            
        Returns:
            Relative path to saved file
        """
        cls._ensure_upload_dirs()
        
        # Validate extension
        ext = cls._get_file_extension(file.filename)
        if ext not in cls.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(cls.ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate size
        if len(content) > cls.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {cls.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        # Generate unique filename
        filename = cls._generate_unique_filename(file.filename)
        file_path = cls.PROFILE_DIR / filename
        
        # Save and optimize image
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Optimize image
            with Image.open(file_path) as img:
                # Convert RGBA to RGB if needed
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # Resize if larger than max_size
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized
                img.save(file_path, optimize=True, quality=85)
            
            return f"/uploads/profiles/{filename}"
        
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    @classmethod
    async def save_logo(
        cls,
        file: UploadFile,
        max_size: Tuple[int, int] = (400, 400)
    ) -> str:
        """
        Save and optimize organization logo
        
        Args:
            file: Uploaded file
            max_size: Maximum dimensions (width, height)
            
        Returns:
            Relative path to saved file
        """
        cls._ensure_upload_dirs()
        
        # Validate extension
        ext = cls._get_file_extension(file.filename)
        if ext not in cls.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(cls.ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate size
        if len(content) > cls.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {cls.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        # Generate unique filename
        filename = cls._generate_unique_filename(file.filename)
        file_path = cls.LOGO_DIR / filename
        
        # Save and optimize logo
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Optimize image
            with Image.open(file_path) as img:
                # Keep transparency for logos if PNG
                if ext == '.png':
                    # Resize maintaining transparency
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True)
                else:
                    # Convert to RGB for other formats
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True, quality=85)
            
            return f"/uploads/logos/{filename}"
        
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Error processing logo: {str(e)}")
    
    @classmethod
    async def save_document(cls, file: UploadFile) -> str:
        """
        Save document file
        
        Args:
            file: Uploaded file
            
        Returns:
            Relative path to saved file
        """
        cls._ensure_upload_dirs()
        
        # Validate extension
        ext = cls._get_file_extension(file.filename)
        if ext not in cls.ALLOWED_DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(cls.ALLOWED_DOCUMENT_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate size
        if len(content) > cls.MAX_DOCUMENT_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {cls.MAX_DOCUMENT_SIZE / 1024 / 1024}MB"
            )
        
        # Generate unique filename
        filename = cls._generate_unique_filename(file.filename)
        file_path = cls.DOCUMENT_DIR / filename
        
        # Save document
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            
            return f"/uploads/documents/{filename}"
        
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Error saving document: {str(e)}")
    
    @classmethod
    def delete_file(cls, file_path: str) -> bool:
        """
        Delete a file by its relative path
        
        Args:
            file_path: Relative path (e.g., "/uploads/profiles/abc.jpg")
            
        Returns:
            True if deleted, False if not found
        """
        # Remove leading slash and create full path
        relative_path = file_path.lstrip('/')
        full_path = Path(relative_path)
        
        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True
        
        return False

