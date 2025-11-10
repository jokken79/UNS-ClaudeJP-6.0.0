/**
 * TypeScript type definitions for UNS-ClaudeJP API
 * Generated from backend Pydantic schemas and SQLAlchemy models
 * Version: 5.4
 */

// ============================================
// ENUMS
// ============================================

export enum UserRole {
  SUPER_ADMIN = 'SUPER_ADMIN',
  ADMIN = 'ADMIN',
  KEITOSAN = 'KEITOSAN',
  TANTOSHA = 'TANTOSHA',
  COORDINATOR = 'COORDINATOR',
  KANRININSHA = 'KANRININSHA',
  EMPLOYEE = 'EMPLOYEE',
  CONTRACT_WORKER = 'CONTRACT_WORKER',
}

export enum CandidateStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  HIRED = 'hired',
}

export enum DocumentType {
  RIREKISHO = 'rirekisho',
  ZAIRYU_CARD = 'zairyu_card',
  LICENSE = 'license',
  CONTRACT = 'contract',
  OTHER = 'other',
}

export enum RequestType {
  YUKYU = 'yukyu',
  HANKYU = 'hankyu',
  IKKIKOKOKU = 'ikkikokoku',
  TAISHA = 'taisha',
}

export enum RequestStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
}

export enum ShiftType {
  ASA = 'asa',
  HIRU = 'hiru',
  YORU = 'yoru',
  OTHER = 'other',
}

// ============================================
// COMMON TYPES
// ============================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  skip?: number;
  limit?: number;
  search?: string;
  sort?: string;
  status_filter?: string;
}

// ============================================
// AUTH TYPES
// ============================================

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  password_hash?: string;
  role: UserRole;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  role?: UserRole;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  password?: string;
}
