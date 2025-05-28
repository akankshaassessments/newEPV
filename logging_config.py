"""
Logging configuration for the EPV application.
Provides different logging levels for development and production environments.
"""

import os
import logging
import logging.handlers
from datetime import datetime


def setup_logging(app):
    """
    Set up logging configuration based on environment.
    
    Args:
        app: Flask application instance
    """
    # Get environment
    flask_env = os.environ.get('FLASK_ENV', 'production')
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging level based on environment
    if flask_env == 'development':
        log_level = logging.DEBUG
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        log_level = logging.INFO
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[]
    )
    
    # Create formatters
    formatter = logging.Formatter(log_format)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'epv_app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Error file handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'epv_errors.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Console handler for development
    if flask_env == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(log_level)
    
    # Configure other loggers
    loggers = [
        'werkzeug',
        'sqlalchemy.engine',
        'googleapiclient.discovery',
        'google.auth.transport.requests'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING if flask_env == 'production' else logging.INFO)
        logger.addHandler(file_handler)
    
    app.logger.info(f"Logging configured for {flask_env} environment")


def get_logger(name):
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Name of the logger (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
