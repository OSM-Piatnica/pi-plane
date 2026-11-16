# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0156_user_notification_preference_group_assignment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Initiative',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('kind', models.CharField(choices=[('goal', 'Goal'), ('initiative', 'Initiative')], default='initiative', max_length=20)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('description_html', models.TextField(blank=True, default='<p></p>')),
                ('start_date', models.DateField(blank=True, null=True)),
                ('target_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('planned', 'Planned'), ('active', 'Active'), ('paused', 'Paused'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='planned', max_length=20)),
                ('health', models.CharField(blank=True, choices=[('on_track', 'On track'), ('at_risk', 'At risk'), ('off_track', 'Off track')], max_length=20, null=True)),
                ('logo_props', models.JSONField(blank=True, default=dict)),
                ('color', models.CharField(blank=True, default='', max_length=255)),
                ('sort_order', models.FloatField(default=65535)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('lead', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='initiative_leads', to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='db.initiative')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiatives', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Initiative',
                'verbose_name_plural': 'Initiatives',
                'db_table': 'initiatives',
                'ordering': ('sort_order', '-created_at'),
            },
        ),
        migrations.CreateModel(
            name='InitiativeEpic',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('initiative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='epic_links', to='db.initiative')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiative_links', to='db.issue')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiative_epics', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Initiative Epic',
                'verbose_name_plural': 'Initiative Epics',
                'db_table': 'initiative_epics',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='InitiativeProject',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('initiative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_links', to='db.initiative')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiative_links', to='db.project')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiative_projects', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Initiative Project',
                'verbose_name_plural': 'Initiative Projects',
                'db_table': 'initiative_projects',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='InitiativeUpdate',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('health', models.CharField(choices=[('on_track', 'On track'), ('at_risk', 'At risk'), ('off_track', 'Off track')], max_length=20)),
                ('text', models.TextField(blank=True, default='')),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='initiative_updates', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('initiative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updates', to='db.initiative')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiative_updates', to='db.workspace')),
            ],
            options={
                'verbose_name': 'Initiative Update',
                'verbose_name_plural': 'Initiative Updates',
                'db_table': 'initiative_updates',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='initiative',
            index=models.Index(fields=['workspace', 'kind'], name='initiative_workspace_kind_idx'),
        ),
        migrations.AddConstraint(
            model_name='initiative',
            constraint=models.CheckConstraint(condition=models.Q(('kind', 'initiative'), ('parent__isnull', True), _connector='OR'), name='initiative_goal_has_no_parent'),
        ),
        migrations.AddConstraint(
            model_name='initiative',
            constraint=models.CheckConstraint(condition=models.Q(('start_date__isnull', True), ('target_date__isnull', True), ('start_date__lte', models.F('target_date')), _connector='OR'), name='initiative_start_date_not_after_target_date'),
        ),
        migrations.AddConstraint(
            model_name='initiativeepic',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('initiative', 'issue'), name='initiative_epic_unique_initiative_issue_when_deleted_at_null'),
        ),
        migrations.AddConstraint(
            model_name='initiativeproject',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('initiative', 'project'), name='initiative_project_unique_initiative_project_when_deleted_at_null'),
        ),
    ]
