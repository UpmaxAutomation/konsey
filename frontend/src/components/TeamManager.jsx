import { useState, useEffect } from 'react';
import { api } from '../api';
import './TeamManager.css';

export default function TeamManager({ onClose }) {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDescription, setNewTeamDescription] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      const response = await api.listTeams();
      setTeams(response.teams || []);
    } catch (error) {
      console.error('Failed to load teams:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTeamDetails = async (teamId) => {
    try {
      const team = await api.getTeam(teamId);
      setSelectedTeam(team);
    } catch (error) {
      console.error('Failed to load team:', error);
    }
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;

    try {
      const team = await api.createTeam({
        name: newTeamName.trim(),
        description: newTeamDescription.trim(),
      });
      setTeams([...teams, team]);
      setNewTeamName('');
      setNewTeamDescription('');
      setShowCreateForm(false);
      setSelectedTeam(team);
    } catch (error) {
      console.error('Failed to create team:', error);
    }
  };

  const handleDeleteTeam = async (teamId) => {
    if (!confirm('Are you sure you want to delete this team?')) return;

    try {
      await api.deleteTeam(teamId);
      setTeams(teams.filter(t => t.id !== teamId));
      if (selectedTeam?.id === teamId) {
        setSelectedTeam(null);
      }
    } catch (error) {
      console.error('Failed to delete team:', error);
    }
  };

  const handleInviteMember = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim() || !selectedTeam) return;

    try {
      await api.inviteTeamMember(selectedTeam.id, inviteEmail.trim(), inviteRole);
      await loadTeamDetails(selectedTeam.id);
      setInviteEmail('');
      setShowInviteForm(false);
    } catch (error) {
      console.error('Failed to invite member:', error);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!selectedTeam) return;

    try {
      await api.removeTeamMember(selectedTeam.id, memberId);
      await loadTeamDetails(selectedTeam.id);
    } catch (error) {
      console.error('Failed to remove member:', error);
    }
  };

  if (loading) {
    return (
      <div className="team-manager">
        <div className="team-manager-header">
          <h2>Team Workspaces</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="loading">Loading teams...</div>
      </div>
    );
  }

  return (
    <div className="team-manager">
      <div className="team-manager-header">
        <h2>Team Workspaces</h2>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="team-manager-content">
        {/* Team List */}
        <div className="team-list-section">
          <div className="section-header">
            <h3>Your Teams</h3>
            <button
              className="add-team-btn"
              onClick={() => setShowCreateForm(true)}
            >
              + New Team
            </button>
          </div>

          {showCreateForm && (
            <form className="create-team-form" onSubmit={handleCreateTeam}>
              <input
                type="text"
                placeholder="Team name"
                value={newTeamName}
                onChange={(e) => setNewTeamName(e.target.value)}
                autoFocus
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={newTeamDescription}
                onChange={(e) => setNewTeamDescription(e.target.value)}
              />
              <div className="form-actions">
                <button type="submit">Create</button>
                <button type="button" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="team-list">
            {teams.length === 0 ? (
              <p className="no-teams">No teams yet. Create one to get started!</p>
            ) : (
              teams.map((team) => (
                <div
                  key={team.id}
                  className={`team-item ${selectedTeam?.id === team.id ? 'selected' : ''}`}
                  onClick={() => loadTeamDetails(team.id)}
                >
                  <div className="team-icon">👥</div>
                  <div className="team-info">
                    <div className="team-name">{team.name}</div>
                    <div className="team-meta">
                      {team.member_count} member{team.member_count !== 1 ? 's' : ''}
                    </div>
                  </div>
                  <button
                    className="delete-team-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteTeam(team.id);
                    }}
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Team Details */}
        {selectedTeam && (
          <div className="team-details-section">
            <div className="section-header">
              <h3>{selectedTeam.name}</h3>
            </div>

            {selectedTeam.description && (
              <p className="team-description">{selectedTeam.description}</p>
            )}

            {/* Members */}
            <div className="members-section">
              <div className="subsection-header">
                <h4>Members</h4>
                <button
                  className="invite-btn"
                  onClick={() => setShowInviteForm(true)}
                >
                  + Invite
                </button>
              </div>

              {showInviteForm && (
                <form className="invite-form" onSubmit={handleInviteMember}>
                  <input
                    type="email"
                    placeholder="Email address"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    autoFocus
                  />
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                  </select>
                  <div className="form-actions">
                    <button type="submit">Invite</button>
                    <button type="button" onClick={() => setShowInviteForm(false)}>
                      Cancel
                    </button>
                  </div>
                </form>
              )}

              <div className="members-list">
                {(selectedTeam.members || []).map((member, idx) => (
                  <div key={member.id || idx} className="member-item">
                    <div className="member-avatar">
                      {member.email?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div className="member-info">
                      <div className="member-email">
                        {member.email || member.user_id}
                      </div>
                      <div className="member-role">{member.role}</div>
                    </div>
                    {member.role !== 'owner' && (
                      <button
                        className="remove-member-btn"
                        onClick={() => handleRemoveMember(member.id)}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Shared Conversations */}
            <div className="conversations-section">
              <div className="subsection-header">
                <h4>Shared Conversations</h4>
              </div>

              <div className="shared-conversations-list">
                {(selectedTeam.conversations || []).length === 0 ? (
                  <p className="no-conversations">
                    No conversations shared yet. Share a conversation from the sidebar.
                  </p>
                ) : (
                  selectedTeam.conversations.map((conv, idx) => (
                    <div key={idx} className="shared-conversation-item">
                      <div className="conv-icon">💬</div>
                      <div className="conv-info">
                        <div className="conv-title">{conv.title}</div>
                        <div className="conv-meta">
                          Shared {new Date(conv.shared_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
