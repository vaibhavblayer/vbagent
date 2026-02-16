"""Tests for batch processing database and utilities."""

import tempfile
from pathlib import Path

import pytest

from vbagent.models.batch import BatchDatabase, ProcessingStatus


class TestBatchDatabase:
    """Tests for BatchDatabase."""
    
    def test_database_creation(self):
        """Test database is created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            # Check database file exists
            db_path = Path(tmpdir) / ".vbagent_batch.db"
            assert db_path.exists()
            
            db.close()
    
    def test_save_and_get_config(self):
        """Test saving and retrieving configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            db.save_config(
                images_dir="./images",
                output_dir="./output",
                variant_types=["numerical", "context"],
                generate_alternates=True,
            )
            
            config = db.get_config()
            assert config is not None
            assert config["images_dir"] == "./images"
            assert config["output_dir"] == "./output"
            assert config["variant_types"] == ["numerical", "context"]
            assert config["generate_alternates"] is True
            
            db.close()
    
    def test_add_image(self):
        """Test adding images to the queue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            image_id = db.add_image("test/image1.png")
            assert image_id > 0
            
            # Adding same image returns same ID
            same_id = db.add_image("test/image1.png")
            assert same_id == image_id
            
            # Adding different image returns different ID
            other_id = db.add_image("test/image2.png")
            assert other_id != image_id
            
            db.close()
    
    def test_update_status(self):
        """Test updating image status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            image_id = db.add_image("test/image.png")
            
            db.update_status(image_id, ProcessingStatus.SCANNING, "scanning")
            
            record = db.get_image(image_id)
            assert record.status == ProcessingStatus.SCANNING
            assert record.current_stage == "scanning"
            
            db.close()
    
    def test_save_and_get_variants(self):
        """Test saving and retrieving variants."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            image_id = db.add_image("test/image.png")
            
            db.save_variant(image_id, "numerical", "\\item Numerical variant")
            db.save_variant(image_id, "context", "\\item Context variant")
            
            variants = db.get_variants(image_id)
            assert len(variants) == 2
            assert variants["numerical"] == "\\item Numerical variant"
            assert variants["context"] == "\\item Context variant"
            
            db.close()
    
    def test_save_and_get_alternates(self):
        """Test saving and retrieving alternates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            image_id = db.add_image("test/image.png")
            
            db.save_alternate(image_id, "Alternate solution 1")
            db.save_alternate(image_id, "Alternate solution 2")
            
            alternates = db.get_alternates(image_id)
            assert len(alternates) == 2
            assert "Alternate solution 1" in alternates
            assert "Alternate solution 2" in alternates
            
            db.close()
    
    def test_get_stats(self):
        """Test getting processing statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            # Add some images with different statuses
            id1 = db.add_image("test/image1.png")
            id2 = db.add_image("test/image2.png")
            id3 = db.add_image("test/image3.png")
            
            db.update_status(id1, ProcessingStatus.COMPLETED)
            db.update_status(id2, ProcessingStatus.FAILED, error="Test error")
            # id3 stays pending
            
            stats = db.get_stats()
            assert stats["total"] == 3
            assert stats["completed"] == 1
            assert stats["failed"] == 1
            assert stats["pending"] == 1
            
            db.close()
    
    def test_reset_failed(self):
        """Test resetting failed images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            id1 = db.add_image("test/image1.png")
            id2 = db.add_image("test/image2.png")
            
            db.update_status(id1, ProcessingStatus.FAILED, error="Error 1")
            db.update_status(id2, ProcessingStatus.FAILED, error="Error 2")
            
            count = db.reset_failed()
            assert count == 2
            
            record1 = db.get_image(id1)
            record2 = db.get_image(id2)
            
            assert record1.status == ProcessingStatus.PENDING
            assert record2.status == ProcessingStatus.PENDING
            assert record1.error_message is None
            
            db.close()
    
    def test_get_pending_images(self):
        """Test getting pending images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = BatchDatabase(base_dir=tmpdir)
            
            id1 = db.add_image("test/image1.png")
            id2 = db.add_image("test/image2.png")
            id3 = db.add_image("test/image3.png")
            
            db.update_status(id1, ProcessingStatus.COMPLETED)
            db.update_status(id2, ProcessingStatus.SCANNING)
            # id3 stays pending
            
            pending = db.get_pending_images()
            
            # Should include pending and in-progress, not completed
            assert len(pending) == 2
            paths = [r.image_path for r in pending]
            assert "test/image2.png" in paths
            assert "test/image3.png" in paths
            
            db.close()
