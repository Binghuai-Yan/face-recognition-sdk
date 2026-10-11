/// <reference types="node" />
import { Readable } from 'stream';
export type Image = string | Buffer | Readable;
export interface Config {
  apiUrl: string;
  apiKey?: string;
  apiKeys?: Partial<Record<'detection' | 'recognition' | 'verification', string>>;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
  comparisonThreshold?: number;
}
export interface Face {
  box: {probability?: number; x_min?: number; y_min?: number; x_max?: number; y_max?: number};
  confidence: number;
  embedding?: number[];
  [plugin: string]: unknown;
}
export interface DetectionResult { faces: Face[]; face_count: number; result?: Face[] }
export interface CompareResult { similarity: number; threshold: number; is_match: boolean; face1: Face; face2: Face }
export interface Match { subject: string; similarity: number; is_match: boolean; face: Face }
export interface SearchResult { results: Match[]; face_count: number }
export interface Subject { subject: string }
export interface FaceRecord { image_id: string; subject: string }
export class FaceSDKError extends Error { errorCode?: string; httpStatusCode?: number }
export class APIError extends FaceSDKError {}
export class NoFaceError extends FaceSDKError {}
export class FaceSDKClient {
  constructor(config: Config);
  detect(image: Image, options?: Record<string, string | number | boolean>): Promise<DetectionResult>;
  compare(source: Image, target: Image): Promise<CompareResult>;
  search(image: Image, limit?: number, threshold?: number): Promise<SearchResult>;
  extractFeature(image: Image): Promise<string>;
  createSubject(subjectId: string, name?: string): Promise<Subject>;
  deleteSubject(subjectId: string): Promise<void>;
  listSubjects(): Promise<Subject[]>;
  addFace(subjectId: string, image: Image, metadata?: Record<string, unknown> | null): Promise<FaceRecord>;
  deleteFace(faceId: string): Promise<void>;
}
