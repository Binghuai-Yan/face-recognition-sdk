INSERT INTO model (guid, name, type, api_key) VALUES 
('35c3545d-855b-417f-9600-e0fcddf2726f', 'FaceSDK Recognition', 'R', '8ac3c230-4402-4cb6-a244-867ad0a696f9'),
('97bb2f04-b9d6-428d-ab26-1a4e564df487', 'FaceSDK Detection', 'D', '9cf54e80-efd9-4e56-831c-8cbb0a8dde05'),
('391a9f82-c620-4432-bc37-9d8a923df4a5', 'FaceSDK Verification', 'V', 'e2207ac4-d5eb-42e8-96ab-92605145c330'),
('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'FaceSDK Anti-spoofing', 'A', 'f47ac10b-58cc-4372-a567-0e02b2c3d479')
ON CONFLICT DO NOTHING;
SELECT guid, name, type, api_key FROM model;
