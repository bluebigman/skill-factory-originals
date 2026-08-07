#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image, ImageOps
import datetime

def resize_image(input_path, output_path, width, height, keep_aspect=False, quality=85, overwrite=False):
    """
    Resize a single image.
    
    Args:
        input_path: Path to input image
        output_path: Path to save resized image
        width: Target width (int or None)
        height: Target height (int or None)
        keep_aspect: If True, maintain aspect ratio when only one dimension is given
        quality: JPEG quality (1-100)
        overwrite: If True, overwrite existing output files
    
    Returns:
        True on success, False on failure
    """
    try:
        # Validate dimensions
        if width is not None and width <= 0:
            print(f"Error resizing {input_path}: width must be > 0")
            return False
        if height is not None and height <= 0:
            print(f"Error resizing {input_path}: height must be > 0")
            return False
        
        # Check if output file exists and overwrite is not allowed
        if os.path.exists(output_path) and not overwrite:
            print(f"Skipping {input_path}: output file exists (use --overwrite to replace)")
            return False
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with Image.open(input_path) as img:
            # Handle EXIF orientation
            img = ImageOps.exif_transpose(img)
            
            orig_w, orig_h = img.size
            
            # Handle None dimensions
            if width is None and height is None:
                # No resize needed, just copy
                ext = os.path.splitext(output_path)[1].lower()
                format_map = {
                    '.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG',
                    '.gif': 'GIF', '.bmp': 'BMP', '.tiff': 'TIFF',
                    '.webp': 'WEBP'
                }
                fmt = format_map.get(ext, None)
                if fmt:
                    img.save(output_path, format=fmt, quality=quality)
                else:
                    img.save(output_path, quality=quality)
                return True
            
            if keep_aspect:
                # Maintain aspect ratio
                if width is not None and height is not None:
                    # Both given, use them directly
                    new_size = (width, height)
                elif width is not None:
                    # Only width given, calculate height
                    ratio = width / orig_w
                    new_size = (width, int(orig_h * ratio))
                elif height is not None:
                    # Only height given, calculate width
                    ratio = height / orig_h
                    new_size = (int(orig_w * ratio), height)
                else:
                    return False
            else:
                # Stretch to exact dimensions (or use given dimension, keep other if None)
                new_w = width if width is not None else orig_w
                new_h = height if height is not None else orig_h
                new_size = (new_w, new_h)
            
            # Ensure dimensions are positive
            if new_size[0] <= 0 or new_size[1] <= 0:
                print(f"Error resizing {input_path}: height and width must be > 0")
                return False
            
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Determine format from output extension
            ext = os.path.splitext(output_path)[1].lower()
            format_map = {
                '.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG',
                '.gif': 'GIF', '.bmp': 'BMP', '.tiff': 'TIFF',
                '.webp': 'WEBP'
            }
            fmt = format_map.get(ext, None)
            
            if fmt:
                resized.save(output_path, format=fmt, quality=quality)
            else:
                resized.save(output_path, quality=quality)
            return True
    except Exception as e:
        print(f"Error resizing {input_path}: {e}")
        return False

def batch_resize(input_dir, output_dir, width=None, height=None, 
                 keep_aspect=False, quality=85, recursive=False, 
                 overwrite=False, max_workers=4):
    """
    Resize all images in a directory with parallel processing.
    
    Args:
        input_dir: Source directory
        output_dir: Destination directory
        width: Target width (int or None)
        height: Target height (int or None)
        keep_aspect: Maintain aspect ratio
        quality: JPEG quality
        recursive: Process subdirectories
        overwrite: Overwrite existing files
        max_workers: Number of parallel workers
    
    Returns:
        Tuple (success_count, fail_count)
    """
    if not os.path.isdir(input_dir):
        print(f"Input directory not found: {input_dir}")
        return (0, 0)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    success = 0
    fail = 0
    
    # Supported image extensions
    extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    # Collect all image files
    image_files = []
    
    if recursive:
        # Walk through all subdirectories
        for root, dirs, files in os.walk(input_dir):
            # Calculate relative path
            rel_path = os.path.relpath(root, input_dir)
            if rel_path == '.':
                target_dir = output_dir
            else:
                target_dir = os.path.join(output_dir, rel_path)
            os.makedirs(target_dir, exist_ok=True)
            
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in extensions:
                    input_path = os.path.join(root, filename)
                    output_path = os.path.join(target_dir, filename)
                    image_files.append((input_path, output_path))
    else:
        # Only process files directly in input_dir
        for filename in os.listdir(input_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, filename)
                image_files.append((input_path, output_path))
    
    if not image_files:
        print("No image files found")
        return (0, 0)
    
    print(f"Processing {len(image_files)} images with {max_workers} workers...")
    
    # Process images in parallel with progress bar
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(resize_image, inp, outp, width, height, 
                              keep_aspect, quality, overwrite): (inp, outp)
                for inp, outp in image_files
            }
            
            # Process results with progress bar
            with tqdm(total=len(image_files), desc="Resizing images", unit="img") as pbar:
                for future in as_completed(future_to_path):
                    inp, outp = future_to_path[future]
                    try:
                        result = future.result()
                        if result:
                            success += 1
                        else:
                            fail += 1
                    except Exception as e:
                        print(f"Error processing {inp}: {e}")
                        fail += 1
                    pbar.update(1)
                    pbar.set_postfix(success=success, fail=fail)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
        # The executor will be shut down automatically
        return (success, fail)
    
    return (success, fail)

def selftest():
    """Run self-test to verify functionality."""
    print("Running self-test...")
    
    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix="batch_resize_test_")
    input_dir = os.path.join(test_dir, "input")
    output_dir = os.path.join(test_dir, "output")
    corrupt_dir = os.path.join(test_dir, "corrupt")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(corrupt_dir, exist_ok=True)
    
    try:
        # Create test images
        # 1. JPEG image
        img1 = Image.new('RGB', (200, 100), color='red')
        img1.save(os.path.join(input_dir, "test1.jpg"), quality=90)
        
        # 2. PNG image
        img2 = Image.new('RGBA', (150, 150), color=(0, 255, 0, 128))
        img2.save(os.path.join(input_dir, "test2.png"))
        
        # 3. GIF image
        img3 = Image.new('P', (100, 200), color=0)
        img3.save(os.path.join(input_dir, "test3.gif"))
        
        # 4. Corrupt file (not an image)
        with open(os.path.join(corrupt_dir, "broken.jpg"), 'w') as f:
            f.write("This is not an image file")
        
        # Test 1: Basic resize with both dimensions
        success, fail = batch_resize(input_dir, output_dir, width=100, height=50)
        assert success == 3, f"Test 1 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 1 failed: expected 0 failures, got {fail}"
        
        # Verify output images
        for fname in ["test1.jpg", "test2.png", "test3.gif"]:
            out_path = os.path.join(output_dir, fname)
            assert os.path.exists(out_path), f"Test 1 failed: {fname} not created"
            with Image.open(out_path) as img:
                assert img.size == (100, 50), f"Test 1 failed: {fname} wrong size {img.size}"
        
        # Test 2: Keep aspect ratio (only width)
        output_dir2 = os.path.join(test_dir, "output2")
        success, fail = batch_resize(input_dir, output_dir2, width=50, keep_aspect=True)
        assert success == 3, f"Test 2 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 2 failed: expected 0 failures, got {fail}"
        
        # Verify aspect ratio
        with Image.open(os.path.join(output_dir2, "test1.jpg")) as img:
            assert img.size == (50, 25), f"Test 2 failed: test1.jpg wrong size {img.size}"
        with Image.open(os.path.join(output_dir2, "test2.png")) as img:
            assert img.size == (50, 50), f"Test 2 failed: test2.png wrong size {img.size}"
        with Image.open(os.path.join(output_dir2, "test3.gif")) as img:
            assert img.size == (50, 100), f"Test 2 failed: test3.gif wrong size {img.size}"
        
        # Test 3: Nonexistent input directory
        success, fail = batch_resize(os.path.join(test_dir, "nonexistent"), 
                                     os.path.join(test_dir, "output3"))
        assert success == 0, f"Test 3 failed: expected 0 successes, got {success}"
        assert fail == 0, f"Test 3 failed: expected 0 failures, got {fail}"
        
        # Test 4: Corrupt file handling
        success, fail = batch_resize(corrupt_dir, os.path.join(test_dir, "output4"))
        assert success == 0, f"Test 4 failed: expected 0 successes, got {success}"
        assert fail == 1, f"Test 4 failed: expected 1 failure, got {fail}"
        
        # Test 5: No resize (both None)
        output_dir5 = os.path.join(test_dir, "output5")
        success, fail = batch_resize(input_dir, output_dir5, width=None, height=None)
        assert success == 3, f"Test 5 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 5 failed: expected 0 failures, got {fail}"
        
        # Test 6: Only height specified (no keep_aspect)
        output_dir6 = os.path.join(test_dir, "output6")
        success, fail = batch_resize(input_dir, output_dir6, height=30)
        assert success == 3, f"Test 6 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 6 failed: expected 0 failures, got {fail}"
        
        # Verify height only
        with Image.open(os.path.join(output_dir6, "test1.jpg")) as img:
            assert img.size == (200, 30), f"Test 6 failed: test1.jpg wrong size {img.size}"
        
        # Test 7: Recursive mode
        subdir = os.path.join(input_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)
        img4 = Image.new('RGB', (50, 50), color='blue')
        img4.save(os.path.join(subdir, "test4.png"))
        
        output_dir7 = os.path.join(test_dir, "output7")
        success, fail = batch_resize(input_dir, output_dir7, width=25, recursive=True)
        assert success == 4, f"Test 7 failed: expected 4 successes, got {success}"
        assert fail == 0, f"Test 7 failed: expected 0 failures, got {fail}"
        
        # Verify recursive output
        assert os.path.exists(os.path.join(output_dir7, "subdir", "test4.png")), \
            "Test 7 failed: subdir output not created"
        
        # Test 8: Overwrite behavior
        output_dir8 = os.path.join(test_dir, "output8")
        # First run
        success, fail = batch_resize(input_dir, output_dir8, width=100, height=50)
        assert success == 3, f"Test 8a failed: expected 3 successes, got {success}"
        
        # Second run without overwrite should skip existing files
        success, fail = batch_resize(input_dir, output_dir8, width=100, height=50)
        assert success == 0, f"Test 8b failed: expected 0 successes, got {success}"
        assert fail == 3, f"Test 8b failed: expected 3 failures, got {fail}"
        
        # Third run with overwrite should succeed
        success, fail = batch_resize(input_dir, output_dir8, width=100, height=50, overwrite=True)
        assert success == 3, f"Test 8c failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 8c failed: expected 0 failures, got {fail}"
        
        # Test 9: Format conversion (PNG to JPEG)
        output_dir9 = os.path.join(test_dir, "output9")
        os.makedirs(output_dir9, exist_ok=True)
        # Convert test2.png to test2.jpg
        success, fail = batch_resize(input_dir, output_dir9, width=100, height=100)
        assert success == 3, f"Test 9 failed: expected 3 successes, got {success}"
        
        # Test 10: Parallel processing with multiple workers
        output_dir10 = os.path.join(test_dir, "output10")
        success, fail = batch_resize(input_dir, output_dir10, width=50, height=50, max_workers=8)
        assert success == 3, f"Test 10 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 10 failed: expected 0 failures, got {fail}"
        
        # Test 11: Invalid dimensions (zero and negative)
        output_dir11 = os.path.join(test_dir, "output11")
        success, fail = batch_resize(input_dir, output_dir11, width=0, height=50)
        assert success == 0, f"Test 11a failed: expected 0 successes, got {success}"
        assert fail == 3, f"Test 11a failed: expected 3 failures, got {fail}"
        
        success, fail = batch_resize(input_dir, output_dir11, width=-10, height=50)
        assert success == 0, f"Test 11b failed: expected 0 successes, got {success}"
        assert fail == 3, f"Test 11b failed: expected 3 failures, got {fail}"
        
        # Test 12: Nonexistent output directory (should be created)
        output_dir12 = os.path.join(test_dir, "nonexistent", "nested", "dir")
        success, fail = batch_resize(input_dir, output_dir12, width=100, height=50)
        assert success == 3, f"Test 12 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 12 failed: expected 0 failures, got {fail}"
        assert os.path.exists(output_dir12), "Test 12 failed: output directory not created"
        
        # Test 13: Keep aspect with both dimensions (should use exact dimensions)
        output_dir13 = os.path.join(test_dir, "output13")
        success, fail = batch_resize(input_dir, output_dir13, width=80, height=60, keep_aspect=True)
        assert success == 3, f"Test 13 failed: expected 3 successes, got {success}"
        assert fail == 0, f"Test 13 failed: expected 0 failures, got {fail}"
        with Image.open(os.path.join(output_dir13, "test1.jpg")) as img:
            assert img.size == (80, 60), f"Test 13 failed: test1.jpg wrong size {img.size}"
        
        print("All self-tests passed!")
        return 0
    except AssertionError as e:
        print(f"SELF-TEST FAILED: {e}")
        return 1
