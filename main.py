"""
Main entry point for the Git Commit Reviewer CLI application.
Orchestrates the fetching of commits, LLM evaluation, and report generation.
"""
import sys
import click
from core.git_handler import fetch_recent_commits
from core.llm_reviewer import evaluate_commits
from core.report_server import generate_and_serve_report

def merge_commit_data(git_commits, llm_reviews):
    """
    Merges the original Git metadata with the LLM evaluation results.
    Matches records using the commit hash to ensure data consistency.
    """
    # Create a dictionary for O(1) lookup of LLM reviews by hash
    # This prevents an inefficient O(n^2) nested loop when matching commits to reviews
    reviews_by_hash = {review['hash']: review for review in llm_reviews if 'hash' in review}
    
    merged_list = []
    for commit in git_commits:
        commit_hash = commit.get('hash')
        
        # Only include commits that were successfully evaluated by the LLM
        if commit_hash in reviews_by_hash:
            review = reviews_by_hash[commit_hash]
            merged_list.append({
                'hash': commit_hash,
                'author': commit.get('author'),
                'message': commit.get('message'),
                'timestamp': commit.get('timestamp'),
                'rating': review.get('rating', 'unknown'),
                'reasoning': review.get('reasoning', 'No reasoning provided.')
            })
            
    return merged_list

@click.command()
@click.option('--url', default=None, help='Remote Git repository URL. Defaults to the current working directory.')
def review_commits(url):
    """
    Analyzes recent git commits using an LLM and serves a local HTML report.
    """
    # Fallback to local directory if no remote URL is provided
    target_source = url if url else "."
    
    # Phase 1: Data Extraction
    click.echo(f"Fetching commits from: {target_source}")
    try:
        git_commits = fetch_recent_commits(target_source)
        if not git_commits:
            click.echo("No commits found to evaluate. Exiting.")
            sys.exit(0)
    except Exception as e:
        click.echo(f"Error fetching commits: {e}", err=True)
        sys.exit(1)
        
    # Phase 2: AI Evaluation
    click.echo("Evaluating with AI. This may take a moment...")
    try:
        llm_reviews = evaluate_commits(git_commits)
    except Exception as e:
        click.echo(f"Error during LLM evaluation: {e}", err=True)
        sys.exit(1)
        
    # Phase 3: Data Aggregation
    click.echo("Merging data...")
    merged_data = merge_commit_data(git_commits, llm_reviews)
    
    if not merged_data:
        click.echo("Failed to match any LLM reviews with the original commits. Exiting.", err=True)
        sys.exit(1)
        
    # Phase 4: Report Generation & Serving
    click.echo("Generating report...")
    try:
        generate_and_serve_report(merged_data)
    except Exception as e:
        click.echo(f"Error starting the report server: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    # Execute the Click CLI command
    review_commits()