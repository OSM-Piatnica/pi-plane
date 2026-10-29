# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0149_work_item_duration_working_days'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserGroup',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('source', models.CharField(choices=[('local', 'Local'), ('entra', 'Microsoft Entra'), ('google', 'Google')], default='local', max_length=20)),
                ('external_id', models.CharField(blank=True, max_length=255, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='db.usergroup')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_groups', to='db.workspace')),
            ],
            options={
                'verbose_name': 'User Group',
                'verbose_name_plural': 'User Groups',
                'db_table': 'user_groups',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='UserGroupMember',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('role', models.PositiveSmallIntegerField(choices=[(20, 'Group admin'), (15, 'Member')], default=15)),
                ('managed_externally', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='db.usergroup')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_group_memberships', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_group_members', to='db.workspace')),
            ],
            options={
                'verbose_name': 'User Group Member',
                'verbose_name_plural': 'User Group Members',
                'db_table': 'user_group_members',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='usergroup',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True), ('parent__isnull', False)), fields=('workspace', 'parent', 'name'), name='user_group_unique_name_in_parent_when_deleted_at_null'),
        ),
        migrations.AddConstraint(
            model_name='usergroup',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True), ('parent__isnull', True)), fields=('workspace', 'name'), name='user_group_unique_top_level_name_when_deleted_at_null'),
        ),
        migrations.AddConstraint(
            model_name='usergroup',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True), ('external_id__isnull', False)), fields=('workspace', 'source', 'external_id'), name='user_group_unique_external_id_when_deleted_at_null'),
        ),
        migrations.AddConstraint(
            model_name='usergroupmember',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('group', 'user'), name='user_group_member_unique_group_user_when_deleted_at_null'),
        ),
    ]
