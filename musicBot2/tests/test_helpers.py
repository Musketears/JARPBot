#!/usr/bin/env python3
"""
Unit tests for helper functions
"""

import unittest
import sys
sys.path.append('..')

from utils.helpers import (
    validate_youtube_url, validate_bet_amount, limit_to_4000_chars,
    format_duration, format_balance, create_progress_bar,
    sanitize_filename, get_user_mention, parse_time_string,
    format_time_string, create_error_embed, create_success_embed,
    create_info_embed
)

class TestValidationFunctions(unittest.TestCase):
    """Test validation helper functions"""
    
    def test_validate_youtube_url_valid(self):
        """Test valid YouTube URLs"""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://youtube-nocookie.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(validate_youtube_url(url))
    
    def test_validate_youtube_url_invalid(self):
        """Test invalid YouTube URLs"""
        invalid_urls = [
            "https://www.google.com",
            "https://www.youtube.com/invalid",
            "not a url",
            "https://www.youtube.com/watch",
            "https://youtu.be/",
            ""
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(validate_youtube_url(url))
    
    def test_validate_bet_amount_valid(self):
        """Test valid bet amounts"""
        test_cases = [
            ("10", 100, 10),
            ("all", 100, 100),
            ("50", 200, 50),
            ("1", 10, 1)
        ]
        
        for bet_str, balance, expected in test_cases:
            with self.subTest(bet=bet_str, balance=balance):
                result = validate_bet_amount(bet_str, balance)
                self.assertEqual(result, expected)
    
    def test_validate_bet_amount_invalid(self):
        """Test invalid bet amounts"""
        test_cases = [
            ("0", 100),
            ("-5", 100),
            ("150", 100),  # More than balance
            ("invalid", 100),
            ("", 100)
        ]
        
        for bet_str, balance in test_cases:
            with self.subTest(bet=bet_str, balance=balance):
                result = validate_bet_amount(bet_str, balance)
                self.assertIsNone(result)

class TestFormattingFunctions(unittest.TestCase):
    """Test formatting helper functions"""
    
    def test_limit_to_4000_chars(self):
        """Test character limit function"""
        # Test with short strings
        short_strings = ["Hello", "World", "Test"]
        result = limit_to_4000_chars(short_strings)
        self.assertIn("Hello", result)
        self.assertIn("World", result)
        self.assertIn("Test", result)
        
        # Test with empty list
        result = limit_to_4000_chars([])
        self.assertEqual(result, "No items to display")
        
        # Test with very long strings
        long_string = "A" * 2000
        long_strings = [long_string, long_string]
        result = limit_to_4000_chars(long_strings)
        self.assertIn(long_string, result)
    
    def test_format_duration(self):
        """Test duration formatting"""
        test_cases = [
            (0, "Unknown"),
            (30, "0:30"),
            (65, "1:05"),
            (3661, "61:01"),
            (-5, "Unknown")
        ]
        
        for seconds, expected in test_cases:
            with self.subTest(seconds=seconds):
                result = format_duration(seconds)
                self.assertEqual(result, expected)
    
    def test_format_balance(self):
        """Test balance formatting"""
        test_cases = [
            (0, "$0"),
            (100, "$100"),
            (1000, "$1,000"),
            (1234567, "$1,234,567"),
            (-500, "$-500")
        ]
        
        for amount, expected in test_cases:
            with self.subTest(amount=amount):
                result = format_balance(amount)
                self.assertEqual(result, expected)
    
    def test_create_progress_bar(self):
        """Test progress bar creation"""
        # Test normal progress
        bar = create_progress_bar(5, 10, 10)
        self.assertEqual(len(bar), 10)
        self.assertEqual(bar.count("█"), 5)
        self.assertEqual(bar.count("░"), 5)
        
        # Test full progress
        bar = create_progress_bar(10, 10, 10)
        self.assertEqual(bar.count("█"), 10)
        self.assertEqual(bar.count("░"), 0)
        
        # Test zero progress
        bar = create_progress_bar(0, 10, 10)
        self.assertEqual(bar.count("█"), 0)
        self.assertEqual(bar.count("░"), 10)
        
        # Test zero total
        bar = create_progress_bar(5, 0, 10)
        self.assertEqual(bar.count("█"), 10)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file with spaces.txt"),
            ("file<with>invalid:chars", "file_with_invalid_chars"),
            ("file/with\\path|chars", "file_with_path_chars"),
            ("A" * 300, "A" * 200)  # Test length limit
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = sanitize_filename(input_name)
                self.assertEqual(result, expected)
    
    def test_get_user_mention(self):
        """Test user mention creation"""
        test_cases = [
            (123456789, "<@123456789>"),
            (0, "<@0>"),
            (999999999, "<@999999999>")
        ]
        
        for user_id, expected in test_cases:
            with self.subTest(user_id=user_id):
                result = get_user_mention(user_id)
                self.assertEqual(result, expected)

class TestTimeFunctions(unittest.TestCase):
    """Test time-related helper functions"""
    
    def test_parse_time_string(self):
        """Test time string parsing"""
        test_cases = [
            ("30s", 30),
            ("2m", 120),
            ("1h", 3600),
            ("1h30m", 5400),
            ("2h15m30s", 8130),
            ("", None),
            ("invalid", None),
            ("1h2m3s", 3723)
        ]
        
        for time_str, expected in test_cases:
            with self.subTest(time_str=time_str):
                result = parse_time_string(time_str)
                self.assertEqual(result, expected)
    
    def test_format_time_string(self):
        """Test time string formatting"""
        test_cases = [
            (30, "30s"),
            (120, "2m"),
            (90, "1m30s"),
            (3600, "1h"),
            (3900, "1h5m"),
            (3723, "1h2m3s"),
            (0, "0s")
        ]
        
        for seconds, expected in test_cases:
            with self.subTest(seconds=seconds):
                result = format_time_string(seconds)
                self.assertEqual(result, expected)

class TestEmbedFunctions(unittest.TestCase):
    """Test embed creation functions"""
    
    def test_create_error_embed(self):
        """Test error embed creation"""
        message = "Test error message"
        embed = create_error_embed(message)
        
        self.assertEqual(embed.title, "❌ Error")
        self.assertEqual(embed.description, message)
        self.assertEqual(embed.color, 0xE02B2B)
    
    def test_create_success_embed(self):
        """Test success embed creation"""
        message = "Test success message"
        embed = create_success_embed(message)
        
        self.assertEqual(embed.title, "✅ Success")
        self.assertEqual(embed.description, message)
        self.assertEqual(embed.color, 0x57F287)
    
    def test_create_info_embed(self):
        """Test info embed creation"""
        title = "Test Title"
        message = "Test info message"
        embed = create_info_embed(title, message)
        
        self.assertEqual(embed.title, title)
        self.assertEqual(embed.description, message)
        self.assertEqual(embed.color, 0xBEBEFE)

if __name__ == '__main__':
    unittest.main() 