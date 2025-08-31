# Jamf Pro Policy Management

> **Complete guide to department-based policy application in Jamf Pro**

---

## Table of Contents

- [Overview](#overview)
- [How Policies Work](#how-policies-work)
- [Department Configuration](#department-configuration)
- [Smart Groups Setup](#smart-groups-setup)
- [API Integration](#api-integration)
- [Policy Examples](#policy-examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Jamf Pro Bootstrap API automatically applies department-specific policies to computers by adding them to Smart Groups. This system ensures that each employee receives the appropriate software, settings, and permissions based on their department.

### Policy Application Flow

1. **CRM sends employee data** with department information
2. **API creates computer record** in Jamf Pro
3. **API adds computer to department Smart Group**
4. **Jamf Pro applies policies** to the Smart Group
5. **Device receives policies** on next check-in

---

## How Policies Work

### Smart Groups and Policies

In Jamf Pro, policies are applied to computers through Smart Groups. The API uses this mechanism to automatically assign policies based on employee department.

#### Smart Group Structure

```
Department Smart Group → Policy Assignment → Computer Membership
```

#### Policy Application Process

1. **Computer Creation**: API creates computer record in Jamf Pro
2. **Group Assignment**: API adds computer to department-specific Smart Group
3. **Policy Trigger**: Jamf Pro detects new computer in Smart Group
4. **Policy Execution**: Jamf Pro applies assigned policies to computer
5. **Device Update**: Computer receives policies on next check-in

### Department Mapping

| Department | Smart Group | Description |
|------------|-------------|-------------|
| **IT** | `IT_Computers` | Developers and system administrators |
| **HR** | `HR_Computers` | HR department employees |
| **Finance** | `FINANCE_Computers` | Finance department |
| **Marketing** | `MARKETING_Computers` | Marketing department |
| **Sales** | `SALES_Computers` | Sales department |
| **Default** | `DEFAULT_Computers` | Other departments |

---

## Department Configuration

### IT Department

#### Smart Group: `IT_Computers`
- **Criteria**: Department = "IT"
- **Scope**: All IT department computers

#### Applied Policies

| Policy Name | Description | Purpose |
|-------------|-------------|---------|
| **IT_Admin_Rights** | Administrative privileges | Grant sudo access and admin rights |
| **IT_Developer_Tools** | Development software | Install Xcode, VS Code, Git, etc. |
| **IT_Server_Access** | Server access tools | VPN, SSH keys, server management |
| **IT_Advanced_Security** | Enhanced security | Advanced security settings and monitoring |

#### Policy Configuration Example

```xml
<!-- IT_Admin_Rights Policy -->
<policy>
    <general>
        <name>IT_Admin_Rights</name>
        <enabled>true</enabled>
        <trigger>EVENT</trigger>
        <trigger_events>
            <trigger_event>Smart Group Membership</trigger_event>
        </trigger_events>
    </general>
    <scope>
        <computer_groups>
            <computer_group>
                <name>IT_Computers</name>
            </computer_group>
        </computer_groups>
    </scope>
    <maintenance>
        <update_inventory>true</update_inventory>
        <reset_name>false</reset_name>
        <install_all_cached_packages>false</install_all_cached_packages>
    </maintenance>
</policy>
```

### HR Department

#### Smart Group: `HR_Computers`
- **Criteria**: Department = "HR"
- **Scope**: All HR department computers

#### Applied Policies

| Policy Name | Description | Purpose |
|-------------|-------------|---------|
| **HR_Basic_Apps** | Basic applications | Office, browsers, standard software |
| **HR_Limited_Rights** | Limited user privileges | Standard user accounts, no admin access |
| **HR_Privacy_Policy** | Privacy settings | Enhanced privacy and data protection |
| **HR_Systems_Access** | HR systems access | Access to HR-specific applications |

### Finance Department

#### Smart Group: `FINANCE_Computers`
- **Criteria**: Department = "Finance"
- **Scope**: All Finance department computers

#### Applied Policies

| Policy Name | Description | Purpose |
|-------------|-------------|---------|
| **Finance_Encryption** | Additional encryption | Enhanced disk encryption and security |
| **Finance_Audit** | Access auditing | Comprehensive audit logging |
| **Finance_Restricted_Install** | Software restrictions | Prevent unauthorized software installation |
| **Finance_Systems_Access** | Financial systems | Access to financial applications |

### Marketing Department

#### Smart Group: `MARKETING_Computers`
- **Criteria**: Department = "Marketing"
- **Scope**: All Marketing department computers

#### Applied Policies

| Policy Name | Description | Purpose |
|-------------|-------------|---------|
| **Marketing_Creative_Apps** | Creative software | Photoshop, Figma, Sketch, etc. |
| **Marketing_Social_Media** | Social media tools | Social media management applications |
| **Marketing_Design_Tools** | Design applications | Design and creative software |

### Sales Department

#### Smart Group: `SALES_Computers`
- **Criteria**: Department = "Sales"
- **Scope**: All Sales department computers

#### Applied Policies

| Policy Name | Description | Purpose |
|-------------|-------------|---------|
| **Sales_CRM_Access** | CRM systems | Access to CRM and sales applications |
| **Sales_Mobile_Policy** | Mobile device policies | Mobile device management settings |
| **Sales_Customer_Tools** | Customer management | Customer relationship tools |

### Default Department

#### Smart Group: `DEFAULT_Computers`
- **Criteria**: Department != "IT,HR,Finance,Marketing,Sales"
- **Scope**: All other department computers

#### Applied Policies

| Policy Name | Description | Purpose |
|-------------|-------------|---------|
| **Default_Basic_Security** | Basic security policies | Standard security settings |
| **Default_Office_Apps** | Standard applications | Office and basic productivity software |
| **Default_Standard_Rights** | Standard user rights | Standard user privileges |

---

## Smart Groups Setup

### Creating Smart Groups in Jamf Pro

#### IT_Computers Smart Group

```xml
<computer_group>
    <name>IT_Computers</name>
    <is_smart>true</is_smart>
    <site>
        <id>-1</id>
        <name>None</name>
    </site>
    <criteria>
        <size>1</size>
        <criterion>
            <name>Department</name>
            <priority>0</priority>
            <and_or>and</and_or>
            <search_type>is</search_type>
            <value>IT</value>
            <opening_paren>false</opening_paren>
            <closing_paren>false</closing_paren>
        </criterion>
    </criteria>
</computer_group>
```

#### HR_Computers Smart Group

```xml
<computer_group>
    <name>HR_Computers</name>
    <is_smart>true</is_smart>
    <site>
        <id>-1</id>
        <name>None</name>
    </site>
    <criteria>
        <size>1</size>
        <criterion>
            <name>Department</name>
            <priority>0</priority>
            <and_or>and</and_or>
            <search_type>is</search_type>
            <value>HR</value>
            <opening_paren>false</opening_paren>
            <closing_paren>false</closing_paren>
        </criterion>
    </criteria>
</computer_group>
```

### Smart Group Criteria

#### Department Field Mapping

The API uses the `Department` field in computer records to determine Smart Group membership. This field is set when the computer record is created.

#### Criteria Examples

```xml
<!-- Finance Department -->
<criterion>
    <name>Department</name>
    <search_type>is</search_type>
    <value>Finance</value>
</criterion>

<!-- Marketing Department -->
<criterion>
    <name>Department</name>
    <search_type>is</search_type>
    <value>Marketing</value>
</criterion>

<!-- Sales Department -->
<criterion>
    <name>Department</name>
    <search_type>is</search_type>
    <value>Sales</value>
</criterion>

<!-- Default (not IT, HR, Finance, Marketing, or Sales) -->
<criterion>
    <name>Department</name>
    <search_type>is not</search_type>
    <value>IT</value>
</criterion>
```

---

## API Integration

### Policy Application Process

#### 1. Computer Creation

```python
def create_computer_with_policies(employee_data):
    """Create computer record and apply policies"""
    
    # Create computer record in Jamf Pro
    computer_result = create_computer_record(employee_data)
    if not computer_result.get('success'):
        return computer_result
    
    jamf_pro_id = computer_result.get('jamf_pro_id')
    department = employee_data.get('department', 'Default')
    
    # Apply department-specific policies
    policy_result = apply_policies_by_department(jamf_pro_id, department)
    
    return {
        'success': True,
        'jamf_pro_id': jamf_pro_id,
        'department': department,
        'policies_applied': policy_result.get('applied_policies', []),
        'message': f'Computer created and policies applied for {department}'
    }
```

#### 2. Smart Group Assignment

```python
def add_computer_to_group(computer_id, group_name):
    """Add computer to department Smart Group"""
    
    # Find group by name
    groups = get_smart_groups()
    group_id = None
    
    for group in groups.get('computer_groups', []):
        if group.get('name') == group_name:
            group_id = group.get('id')
            break
    
    if not group_id:
        return {
            'success': False,
            'error': f'Group "{group_name}" not found'
        }
    
    # Add computer to group
    group_data = {
        "computer_additions": [{"id": computer_id}]
    }
    
    result = make_request('PUT', f'/computergroups/id/{group_id}', group_data)
    
    if result:
        return {
            'success': True,
            'group_id': group_id,
            'message': f'Computer added to group {group_name}'
        }
    else:
        return {
            'success': False,
            'error': 'Failed to add computer to group'
        }
```

#### 3. Department Policy Mapping

```python
def apply_policies_by_department(computer_id, department):
    """Apply department-specific policies"""
    
    # Department to Smart Group mapping
    department_groups = {
        'IT': 'IT_Computers',
        'HR': 'HR_Computers',
        'Finance': 'FINANCE_Computers',
        'Marketing': 'MARKETING_Computers',
        'Sales': 'SALES_Computers',
        'Default': 'DEFAULT_Computers'
    }
    
    # Get Smart Group for department
    group_name = department_groups.get(department, 'DEFAULT_Computers')
    
    # Add computer to Smart Group
    result = add_computer_to_group(computer_id, group_name)
    
    if result.get('success'):
        return {
            'success': True,
            'applied_policies': [f'{department} policies'],
            'department': department,
            'smart_group': group_name,
            'message': f'Applied {department} policies'
        }
    else:
        return {
            'success': False,
            'error': result.get('error', 'Unknown error')
        }
```

### API Endpoints

#### Get Policy Information

```http
GET /api/policies
```

**Response:**
```json
{
  "departments": {
    "IT": {
      "smart_group": "IT_Computers",
      "policies": [
        "IT_Admin_Rights - Administrative privileges",
        "IT_Developer_Tools - Xcode, VS Code, Git",
        "IT_Server_Access - VPN, SSH keys",
        "IT_Advanced_Security - Enhanced security settings"
      ]
    },
    "HR": {
      "smart_group": "HR_Computers",
      "policies": [
        "HR_Basic_Apps - Office, browsers",
        "HR_Limited_Rights - Limited user privileges",
        "HR_Privacy_Policy - Privacy settings",
        "HR_Systems_Access - HR systems access"
      ]
    }
  },
  "how_it_works": [
    "1. CRM sends employee data with department field",
    "2. API creates computer record in Jamf Pro",
    "3. API adds computer to department Smart Group",
    "4. Jamf Pro automatically applies policies to group",
    "5. Device receives policies on next check-in"
  ],
  "supported_departments": ["IT", "HR", "Finance", "Marketing", "Sales"],
  "default_fallback": "Default policies applied if department not recognized"
}
```

---

## Policy Examples

### IT Department Policy Example

#### IT_Admin_Rights Policy

```xml
<policy>
    <general>
        <name>IT_Admin_Rights</name>
        <enabled>true</enabled>
        <trigger>EVENT</trigger>
        <trigger_events>
            <trigger_event>Smart Group Membership</trigger_event>
        </trigger_events>
        <frequency>Once per computer</frequency>
        <retry_event>none</retry_event>
        <retry_attempts>-1</retry_attempts>
        <notify_on_each_failed_retry>false</notify_on_each_failed_retry>
        <location_user_only>false</location_user_only>
        <target_drive>/</target_drive>
        <offline>false</offline>
    </general>
    <scope>
        <computer_groups>
            <computer_group>
                <name>IT_Computers</name>
            </computer_group>
        </computer_groups>
    </scope>
    <self_service>
        <use_for_self_service>false</use_for_self_service>
        <self_service_display_name></self_service_display_name>
        <install_button_text>Install</install_button_text>
        <reinstall_button_text>Reinstall</reinstall_button_text>
        <self_service_description></self_service_description>
        <force_users_to_view_description>false</force_users_to_view_description>
        <self_service_icon>
            <id>0</id>
            <filename></filename>
            <uri></uri>
        </self_service_icon>
        <feature_on_main_page>false</feature_on_main_page>
        <self_service_categories>
            <category>
                <name>None</name>
            </category>
        </self_service_categories>
    </self_service>
    <package_configuration>
        <packages>
            <size>0</size>
        </packages>
    </package_configuration>
    <scripts>
        <size>1</size>
        <script>
            <id>1</id>
            <name>Grant Admin Rights</name>
            <priority>After</priority>
            <parameter4></parameter4>
            <parameter5></parameter5>
            <parameter6></parameter6>
            <parameter7></parameter7>
            <parameter8></parameter8>
            <parameter9></parameter9>
            <parameter10></parameter10>
            <parameter11></parameter11>
        </script>
    </scripts>
    <printers>
        <size>0</size>
    </printers>
    <dock_items>
        <size>0</size>
    </dock_items>
    <account_maintenance>
        <accounts>
            <size>0</size>
        </accounts>
        <directory_bindings>
            <size>0</size>
        </directory_bindings>
        <management_account>
            <action>do_not_change</action>
            <managed_password></managed_password>
            <managed_password_length>8</managed_password_length>
        </management_account>
        <open_firmware_efi_password>
            <of_mode>none</of_mode>
            <of_password_sha256></of_password_sha256>
        </open_firmware_efi_password>
    </account_maintenance>
    <maintenance>
        <update_inventory>true</update_inventory>
        <reset_name>false</reset_name>
        <install_all_cached_packages>false</install_all_cached_packages>
        <heal>false</heal>
        <prebindings>false</prebindings>
        <permissions>false</permissions>
        <byhost>false</byhost>
        <system_cache>false</system_cache>
        <user_cache>false</user_cache>
        <verify>false</verify>
    </maintenance>
    <files_processes>
        <search_by_path></search_by_path>
        <delete_file>false</delete_file>
        <locate_file></locate_file>
        <update_locate_database>false</update_locate_database>
        <spotlight_search></spotlight_search>
        <search_for_process></search_for_process>
        <kill_process>false</kill_process>
        <run_command></run_command>
    </files_processes>
    <user_interaction>
        <message_start></message_start>
        <allow_users_to_defer>false</allow_users_to_defer>
        <allow_deferral_until_utc></allow_deferral_until_utc>
        <message_finish></message_finish>
    </user_interaction>
</policy>
```

### HR Department Policy Example

#### HR_Basic_Apps Policy

```xml
<policy>
    <general>
        <name>HR_Basic_Apps</name>
        <enabled>true</enabled>
        <trigger>EVENT</trigger>
        <trigger_events>
            <trigger_event>Smart Group Membership</trigger_event>
        </trigger_events>
        <frequency>Once per computer</frequency>
    </general>
    <scope>
        <computer_groups>
            <computer_group>
                <name>HR_Computers</name>
            </computer_group>
        </computer_groups>
    </scope>
    <package_configuration>
        <packages>
            <size>3</size>
            <package>
                <id>1</id>
                <name>Microsoft Office</name>
                <action>Install</action>
                <fut></fut>
                <feu>false</feu>
            </package>
            <package>
                <id>2</id>
                <name>Google Chrome</name>
                <action>Install</action>
                <fut></fut>
                <feu>false</feu>
            </package>
            <package>
                <id>3</id>
                <name>Slack</name>
                <action>Install</action>
                <fut></fut>
                <feu>false</feu>
            </package>
        </packages>
    </package_configuration>
    <maintenance>
        <update_inventory>true</update_inventory>
    </maintenance>
</policy>
```

---

## Troubleshooting

### Common Issues

#### Policies Not Applied

**Symptoms:**
- Computer appears in Smart Group but policies don't execute
- No policy logs in Jamf Pro
- Device doesn't receive expected software

**Solutions:**

1. **Check Smart Group Criteria**
   ```bash
   # Verify computer is in correct Smart Group
   # Check Department field value matches criteria
   ```

2. **Verify Policy Assignment**
   ```bash
   # Ensure policies are assigned to Smart Group
   # Check policy scope includes Smart Group
   ```

3. **Check Policy Triggers**
   ```bash
   # Verify policy trigger is set to "Smart Group Membership"
   # Check policy frequency settings
   ```

4. **Force Policy Execution**
   ```bash
   # On device, run:
   sudo jamf policy
   
   # Or trigger via Jamf Pro web interface
   ```

#### Computer Not Added to Group

**Symptoms:**
- API returns success but computer not in Smart Group
- Department field not set correctly
- Smart Group not found

**Solutions:**

1. **Check Department Field**
   ```python
   # Verify department value in employee data
   print(f"Department: {employee_data.get('department')}")
   ```

2. **Verify Smart Group Exists**
   ```python
   # Check Smart Group exists in Jamf Pro
   groups = get_smart_groups()
   for group in groups.get('computer_groups', []):
       print(f"Group: {group.get('name')}")
   ```

3. **Check API Permissions**
   ```bash
   # Verify API user has permissions to:
   # - Read computer groups
   # - Update computer groups
   # - Add computers to groups
   ```

#### Policy Execution Errors

**Symptoms:**
- Policies fail to execute
- Error messages in Jamf Pro logs
- Software not installed

**Solutions:**

1. **Check Package Availability**
   ```bash
   # Verify packages exist in Jamf Pro
   # Check package distribution points
   # Ensure packages are accessible
   ```

2. **Review Policy Logs**
   ```bash
   # Check Jamf Pro policy logs
   # Look for specific error messages
   # Verify policy execution history
   ```

3. **Test Policy Manually**
   ```bash
   # Create test policy
   # Apply to single computer
   # Monitor execution manually
   ```

### Debug Commands

#### Check Computer Status

```bash
# On device, check Jamf Pro status
sudo jamf recon
sudo jamf policy
sudo jamf log

# Check policy execution
sudo jamf policy -verbose
```

#### Verify Smart Group Membership

```bash
# Check if computer is in Smart Group
# Via Jamf Pro web interface:
# 1. Go to Computers > Computer Groups
# 2. Select department Smart Group
# 3. Verify computer appears in list
```

#### API Debug Information

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check API responses
response = add_computer_to_group(computer_id, group_name)
print(f"Response: {response}")
```

---

## Support

### Contact Information

- **Email**: sergei@pharmacyhub.com
- **Documentation**: [README.md](README.md)
- **Security**: [SECURITY.md](SECURITY.md)

### Additional Resources

- [Jamf Pro Policy Documentation](https://docs.jamf.com/jamf-pro/documentation/Policy.html)
- [Smart Groups Guide](https://docs.jamf.com/jamf-pro/documentation/Computer_Groups.html)
- [Policy Troubleshooting](https://docs.jamf.com/jamf-pro/documentation/Policy_Troubleshooting.html)

---

<div align="center">

**Policy Management Guide - Last updated: January 2024**

</div>
