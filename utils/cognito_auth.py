#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Cognito authentication for AWS API data source"""

import boto3
from typing import Optional, Tuple


class CognitoAuth:
    """Handle AWS Cognito authentication"""
    
    def __init__(
        self,
        user_pool_id: str,
        client_id: str,
        region: str = "ap-southeast-2"
    ):
        """
        Initialize Cognito authentication
        
        Args:
            user_pool_id: AWS Cognito User Pool ID
            client_id: AWS Cognito App Client ID
            region: AWS region
        """
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self.client = boto3.client('cognito-idp', region_name=region)
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticate user with Cognito
        
        Args:
            username: Username
            password: Password
        
        Returns:
            Tuple of (success, id_token, error_message)
        """
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            # Extract ID token
            id_token = response['AuthenticationResult']['IdToken']
            return True, id_token, None
            
        except self.client.exceptions.NotAuthorizedException:
            return False, None, "Invalid username or password"
        except self.client.exceptions.UserNotFoundException:
            return False, None, "User not found"
        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"
    
    @staticmethod
    def validate_token(id_token: str) -> bool:
        """
        Basic validation that token exists and is not empty
        
        Args:
            id_token: ID token to validate
        
        Returns:
            True if token appears valid
        """
        return bool(id_token and len(id_token) > 20)
