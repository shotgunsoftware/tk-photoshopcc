# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class ContextFieldsDisplay(HookBaseClass):
    """
    Used to control the way the current context fields are displayed.
    """

    def get_entity_fields(self, entity_type):
        """
        Given a particular entity type for the current context, return a list of
        fields to query for display in the header.

        Note: the thumbnail ("image" field) query/display is handled by the
        engine and is not required to be returned by this method.

        :param entity_type: Shotgun entity type to return fields for
        :returns: ``list`` of Shotgun fields
        """

        # supported by all normal fields
        base_fields = [
            "id",
            "type",
            "tag_list",
        ]

        # supported by most entities
        std_fields = base_fields
        std_fields.extend([
            "code",
            "project",
            "sg_status_list",
            "description",
        ])

        # ---- fields for specific entity contexts

        if entity_type == "Project":
            fields = base_fields
            fields.extend([
                "name",
            ])

        elif entity_type == "Asset":
            fields = std_fields
            fields.extend([
                "sg_asset_type",
            ])

        elif entity_type == "Shot":
            fields = std_fields
            fields.extend([
                "sg_cut_in",
                "sg_cut_out",
                "sg_head_in",
                "sg_tail_out",
                "sg_sequence",
            ])

        elif entity_type == "Task":
            fields = base_fields
            fields.extend([
                "task_assignees",
                "due_date",
                "entity",
                "step",
                "sg_status_list",
                "project",
                "content",
            ])

        else:
            fields = std_fields

        return fields

    def get_context_html(self, entity, sg_globals):
        """
        Returns the html used to display the supplied context entity.

        The entity will include all queried fields returned by
        ``get_entity_fields``.

        Note: This typically returns a table of field/value names that will
        display next to the entity's thumbnail. The thumbnail query, download,
        and display is handled by the engine.

        :param entity: Shotgun entity to display context fields for.
        :param sg_globals: A handle on the shotgun globals api provided via
            the shotgunutils framework.
        :returns: List of Shotgun fields

        Here are some css classes that can be used to display text in various
        ways::

            `sg_label` and `sg_label_td`:
                The name of a queried field such as: "Type", "Name", "Shot",
                "Asset", etc.

            `sg_value` and `sg_value_td`:
                The value of a queried field such as: "Character", "Shot01",
                "Bunny", etc.
        """

        if entity is None:
            # site context
            return self._get_site_html()

        entity_type = entity.get("type")

        if entity_type == "Project":
            html = self._get_project_html(entity, sg_globals)
        elif entity_type == "Asset":
            html = self._get_asset_html(entity, sg_globals)
        elif entity_type == "Shot":
            html = self._get_shot_html(entity, sg_globals)
        elif entity_type == "Task":
            html = self._get_task_html(entity, sg_globals)
        else:
            # fallback
            html = self._get_entity_html(entity, sg_globals)

        return html

    def _get_site_html(self):

        site_url = self.parent.sgtk.shotgun_url
        site_display = site_url.split("//")[-1]
        site_link = self.parent.get_panel_link(site_url, site_display)

        return \
            """
            <table>
              <tr>
                <td class='sg_label_td'>Site:</td>
                <td class='sg_value_td'>{name}</td>
              </tr>
            </table>
            """.format(
                name=site_link,
            )

    def _get_project_html(self, entity, sg_globals):
        """Returns html for displaying a project context."""

        project_link = self._get_entity_sg_link(entity["name"], entity)

        return \
            """
            <table>
              <tr>
                <td class='sg_label_td'>Project:</td>
                <td class='sg_value_td'>{name}</td>
              </tr>
            </table>
            """.format(
                name=project_link
            )

    def _get_asset_html(self, entity, sg_globals):
        """Returns html for displaying an asset context."""

        asset_link = self._get_entity_sg_link(entity["code"], entity)

        status = sg_globals.get_status_display_name(
            entity["sg_status_list"],
            project_id=entity["project"]["id"]
        )

        # always include name, type, and status
        html = \
            """
            <table>
              <tr>
                <td class='sg_label_td'>Asset:</td>
                <td class='sg_value_td'>{name}</td>
              </tr>
              <tr>
                <td class='sg_label_td'>Type:</td>
                <td class='sg_value_td'>{type}</td>
              </tr>
              <tr>
                <td class='sg_label_td'>Status:</td>
                <td class='sg_value_td'>{status}</td>
              </tr>
            """.format(
                name=asset_link,
                type=entity["sg_asset_type"],
                status=status,
            )

        # tags if there are any
        if entity["tag_list"]:
            tag_display = ", ".join(entity["tag_list"])
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Tags:</td>
                  <td class='sg_value_td'>{tags}</td>
                </tr>
                """.format(
                    tags=tag_display,
                )

        # description if there is one
        if entity["description"]:
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Desc:</td>
                  <td class='sg_value_td'>{desc}</td>
                </tr>
                """.format(
                    desc=entity["description"]
                )

        # close up the table
        html += "</table>"

        return html

    def _get_shot_html(self, entity, sg_globals):
        """Returns html for displaying a shot context."""

        shot_link = self._get_entity_sg_link(entity["code"], entity)

        status = sg_globals.get_status_display_name(
            entity["sg_status_list"],
            project_id=entity["project"]["id"]
        )

        # by default show the shot url
        shot_display = shot_link

        # include seq name next to shot name if there is one.
        # display it as a field name to allow shot name to stand out
        seq = entity["sg_sequence"]
        if seq:
            seq_name = seq["name"]
            seq_link = self._get_entity_sg_link(seq_name, seq)
            shot_display = \
                """
                {name}&nbsp;<span class='sg_label'>({seq_name})</span>
                """.format(
                    name=shot_link,
                    seq_name=seq_link,
                )

        # always include name, type, and status
        html = \
            """
            <table>
              <tr>
                <td class='sg_label_td'>Shot:</td>
                <td class='sg_value_td'>{name}</td>
              </tr>
              <tr>
                <td class='sg_label_td'>Status:</td>
                <td class='sg_value_td'>{status}</td>
              </tr>
            """.format(
                name=shot_display,
                status=status,
            )

        # tags if there are any
        if entity["tag_list"]:
            tag_display = ", ".join(entity["tag_list"])
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Tags:</td>
                  <td class='sg_value_td'>{tags}</td>
                </tr>
                """.format(
                    tags=tag_display,
                )

        # ---- show some cut info if available

        cut_display = None

        # cut in/out
        if entity["sg_cut_in"] is not None and entity["sg_cut_out"] is not None:
            cut_display = \
                """
                    {cut_in} - {cut_out}
                """.format(
                    cut_in=entity["sg_cut_in"],
                    cut_out=entity["sg_cut_out"]
                )

        # include head/tail if set
        if (cut_display and
           entity["sg_head_in"] is not None and
           entity["sg_tail_out"] is not None):

            cut_display = \
                """
                    <small><span class='sg_label'>{head_in} | </span></small>
                    {cut_display}
                    <small><span class='sg_label'> | {tail_out}</span></small>
                """.format(
                    head_in=entity["sg_head_in"],
                    cut_display=cut_display,
                    tail_out=entity["sg_tail_out"]
                )

        if cut_display:
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Cut:</td>
                  <td class='sg_value_td'>{cut_display}</td>
                </tr>
                """.format(
                    cut_display=cut_display,
                )

        # description if there is one
        if entity["description"]:
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Desc:</td>
                  <td class='sg_value_td'>{desc}</td>
                </tr>
                """.format(
                    desc=entity["description"]
                )

        # close up the table
        html += "</table>"

        return html

    def _get_task_html(self, entity, sg_globals):
        """Returns html for displaying a task context."""

        task_link = self._get_entity_sg_link(entity["content"], entity)

        status = sg_globals.get_status_display_name(
            entity["sg_status_list"],
            project_id=entity["project"]["id"]
        )

        # by default show the shot url
        task_display = task_link

        # include step name next to shot name if not the same.
        # display it as a field name to allow shot name to stand out
        step = entity["step"]
        if step:
            step_name = step["name"]
            if step_name != entity["content"]:
                task_display = \
                    """
                    {name}&nbsp;<span class='sg_label'>({step_name})</span>
                    """.format(
                        name=task_display,
                        step_name=step_name,
                    )

        # always include name and status
        html = \
            """
            <table>
              <tr>
                <td class='sg_label_td'>Task:</td>
                <td class='sg_value_td'>{name}</td>
              </tr>
              <tr>
                <td class='sg_label_td'>Status:</td>
                <td class='sg_value_td'>{status}</td>
              </tr>
            """.format(
                name=task_display,
                status=status,
            )

        # artist
        if entity["task_assignees"]:
            assignee_entities = entity["task_assignees"]
            assignee_links = []
            for assignee_entity in assignee_entities:
                asignee_name = assignee_entity["name"]
                assignee_links.append(
                    self._get_entity_sg_link(asignee_name, assignee_entity)
                )
            assignee_display = ", ".join(assignee_links)
            assignee_label = "Artists" \
                if len(assignee_entities) > 1 else "Artist"
            html += \
                """
                  <tr>
                    <td class='sg_label_td'>{label}:</td>
                    <td class='sg_value_td'>{name}</td>
                  </tr>
                """.format(
                    label=assignee_label,
                    name=assignee_display,
                )

        # due date
        if entity["due_date"]:
            html += \
                """
                  <tr>
                    <td class='sg_label_td'>Due:</td>
                    <td class='sg_value_td'>{date}</td>
                  </tr>
                """.format(
                    date=entity["due_date"],
                )

        # entity
        if entity["entity"]:
            linked_entity = entity["entity"]
            if "name" in linked_entity:
                linked_entity_display = linked_entity["name"]
            else:
                linked_entity_display = linked_entity["code"]

            linked_entity_link = self._get_entity_sg_link(
                linked_entity_display, linked_entity)
            html += \
                """
                  <tr>
                    <td class='sg_label_td'>{entity_type}:</td>
                    <td class='sg_value_td'>{name}</td>
                  </tr>
                """.format(
                    entity_type=linked_entity["type"],
                    name=linked_entity_link,
                )

        # close up the table
        html += "</table>"

        return html

    def _get_entity_html(self, entity, sg_globals):
        """Returns html for displaying a generic entity context."""

        entity_link = self._get_entity_sg_link(entity["code"], entity)

        status = sg_globals.get_status_display_name(
            entity["sg_status_list"],
            project_id=entity.get("project", {}).get("id")
        )

        entity_type = entity["type]"]

        # always include name, type, and status
        html = \
            """
            <table>
              <tr>
                <td class='sg_label_td'>{entity_type}:td>
                <td class='sg_value_td'>{name}</td>
              </tr>
              <tr>
                <td class='sg_label_td'>Status:</td>
                <td class='sg_value_td'>{status}</td>
              </tr>
            """.format(
                entity_type=entity_type,
                name=entity_link,
                status=status,
            )

        # tags if there are any
        if entity["tag_list"]:
            tag_display = ", ".join(entity["tag_list"])
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Tags:</td>
                  <td class='sg_value_td'>{tags}</td>
                </tr>
                """.format(
                    tags=tag_display,
                )

        # description if there is one
        if entity["description"]:
            html += \
                """
                <tr>
                  <td class='sg_label_td'>Desc:</td>
                  <td class='sg_value_td'>{desc}</td>
                </tr>
                """.format(
                    desc=entity["description"]
                )

        # close up the table
        html += "</table>"

        return html

    def _get_entity_sg_link(self, text, entity):
        """
        Given some text, return html formatted link to the given entity in SG.
        """

        url = "%s/detail/%s/%d" % (
            self.parent.sgtk.shotgun_url, entity["type"], entity["id"])

        return self.parent.get_panel_link(url, text)
