# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""An in-memory stand-in for ``S3Storage`` / ``AzureBlobStorage``, for the tests of the native document store."""


class FakeObjectStorage:
    """
    Answers the methods the native document store calls. ``put`` plays the browser sending the bytes to the
    presigned address; ``use_put`` makes it answer like Azure (one PUT) instead of S3 (a form POST).
    """

    def __init__(self, *, use_put=False):
        self.objects = {}
        self.deleted = []
        self.use_put = use_put
        self.presigned_posts = []

    def put(self, key, content: bytes):
        self.objects[key] = content

    def generate_presigned_post(self, object_name, file_type, file_size, expiration=None):
        self.presigned_posts.append({"key": object_name, "type": file_type, "size": file_size})
        if self.use_put:
            return {
                "url": f"https://blob.example.test/uploads/{object_name}?sig=1",
                "fields": {},
                "method": "PUT",
                "headers": {"x-ms-blob-type": "BlockBlob", "Content-Type": file_type},
            }
        return {
            "url": "https://s3.example.test/uploads",
            "fields": {"key": object_name, "Content-Type": file_type, "policy": "p", "x-amz-signature": "s"},
        }

    def get_object_metadata(self, object_name):
        content = self.objects.get(object_name)
        if content is None:
            return None
        return {"ContentType": "application/pdf", "ContentLength": len(content), "ETag": f'"etag-{len(content)}"'}

    def generate_presigned_url(self, object_name, disposition="inline", filename=None, content_type=None, **kwargs):
        return f"https://s3.example.test/uploads/{object_name}?disposition={disposition}&sig=1"

    def iter_object(self, object_name, chunk_size=1024 * 1024):
        content = self.objects[object_name]
        for start in range(0, len(content), 4):
            yield content[start : start + 4]

    def delete_files(self, object_names):
        for name in object_names:
            self.objects.pop(name, None)
            self.deleted.append(name)
        return True
