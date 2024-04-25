% ============ Identification ============ %
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{SolutionManual}[04/24/2024 Solution Manual Template]

% ============ Preliminary declarations ============ %
\LoadClass{report}

% Packages
\RequirePackage[most]{tcolorbox} % for problem environment
\RequirePackage{fancyhdr, lastpage, hyperref} % for headers and footers
\RequirePackage{titlesec, xcolor, etoolbox} % for title section
\RequirePackage{geometry} % for page layout
\RequirePackage{tocloft} % for table of contents
\RequirePackage{bold-extra} % for bold + small caps
\RequirePackage{graphicx, float} % for figures

% ============ Figures path ============ %
\graphicspath{ {./Figures/} } % images folder

% ============ Page layout ============ %
 \geometry{
    a4paper,
    margin=25mm,
 }

% ============ Table of contents ============ %
\renewcommand{\cfttoctitlefont}{\scshape\huge} % title font
\renewcommand{\contentsname}{\centering\scshape Table of Contents\par} % title name
\renewcommand{\cftaftertoctitle}{\noindent\rule{\textwidth}{0.8pt}} % horizontal line

\renewcommand{\cftchapfont}{\bfseries \scshape} % chapter font

% ============ Colors ============ %
\colorlet{ThemeColor}{red!50!black}
\hypersetup{
    colorlinks,
    linkcolor=ThemeColor
}

% ============ Chapter ============ %
\titleformat{\chapter}[display]
  {\centering}
  {\hypertarget{\thechapter}{\huge \scshape Chapter \textcolor{ThemeColor}{\Huge\bfseries \thechapter}.}}
  {1ex}
  {\titlerule[0.8pt] \LARGE \scshape}

% ============ Problems environment ============ %
% Set up counters for problems and subproblems
\newcounter{ProblemNum}[chapter]
\renewcommand{\theProblemNum}{\arabic{ProblemNum}}
\newcounter{SubProblemNum}
\setcounter{SubProblemNum}{1}
\renewcommand{\theSubProblemNum}{(\alph{SubProblemNum})}

% Define question environment
\newtcolorbox{question}{enhanced,
                      colback=gray!5!white,
                      colframe=gray!50!black,
                      title=\hypertarget{\thechapter-\theProblemNum}{\scshape Problem \theProblemNum}.
                      }

% Define subproblem environment
\newtcolorbox{subquestion}{enhanced,
                           colback=gray!5!white,
                           colframe=gray!75!black,
                           title=\theSubProblemNum
                          }

% Define solution command
\newcommand*{\solution}{%
  {\scshape Solution:}
  }

% Define answer environment
\newtcolorbox{answer}{enhanced,
                      colback=red!5!white,
                      colframe=ThemeColor,
                      title=\scshape Answer to Problem \theProblemNum.
                      }

% Define subanswer environment
\newtcolorbox{subanswer}{enhanced,
                         colback=red!5!white,
                         colframe=red!50!black,
                         title=Answer to Problem \theProblemNum~\theSubProblemNum. 
                         }

% Wrapper for problems
% #1 = Question
% #2 = Solution
% #3 = Answer
\newenvironment{problem}[3]
{
    \newpage
    \refstepcounter{ProblemNum}\label{\thechapter-\theProblemNum}%
    \pdfbookmark[1]{Problem \theProblemNum}{problem\thechapter-\theProblemNum} % Add bookmark
    \setcounter{SubProblemNum}{1}
    \addtocontents{toc}{\hspace{2em}\protect\hyperlink{\thechapter-\theProblemNum}{\scshape Problem~\theProblemNum.}\hspace{0.5em}\dotfill\thepage\par}
    \begin{question}
        #1
    \end{question}
    \ifx&#2&%
        % #2 is empty
    \else
        \solution
            #2
    \fi
    \ifx&#3&%
        % #3 is empty
    \else
        \begin{answer}
            #3
        \end{answer}
    \fi
}{}

% Wrapper for subproblems
% #1 = Question
% #2 = Solution
% #3 = Answer
\newenvironment{subproblem}[3]
{
    \begin{subquestion}
        #1
    \end{subquestion}
    \solution
        #2
    \begin{subanswer}
        #3
    \end{subanswer}
}
{
    \refstepcounter{SubProblemNum}
}

% References
% #1 = Champter number
% #2 = Problem number
\newcommand{\probref}[2]{\hyperlink{#1-#2}{Chap. #1 Prob. #2}}

% ============ Title Page ============ %
\renewcommand{\maketitle}{%
\begin{titlepage}
        \center
        \textsc{\Large My Humble Solution to}\\[1.5cm]
        \textsc{\LARGE \firstTitle}\\[0.5cm] % Major heading such as cours
        \noindent\rule{\textwidth}{0.8pt}\\[0.4cm]
        \textsc{\huge\bfseries \textcolor{ThemeColor}{\mainTitle}}\\[0.5cm]
        \noindent\rule{\textwidth}{0.8pt}\\[1.5cm]
        \large
        \textit{Author}\\
        \authorName % Your name
        \vfill
        \today
\end{titlepage}
}

% ============ Headers and footers ============ %
\renewcommand{\chaptermark}[1]{\markboth{#1}{}}
\pagestyle{fancy}
\fancyhf{} % clear existing header/footer entries

% Only footer for chapter page
\fancypagestyle{plain}{%
\fancyhf{}%
\renewcommand{\headrulewidth}{0.0pt}%
\fancyfoot[L]{\footnotesize \scshape Solution to \mainTitle~by \authorName}
\fancyfoot[R]{\footnotesize \scshape Page \thepage\ of \pageref{LastPage}}}

% Header and footer for other pages
\fancyfoot[L]{\footnotesize \scshape Solution to \mainTitle~by \authorName}
\fancyfoot[R]{\footnotesize \scshape Page \thepage\ of \pageref{LastPage}}
\fancyhead[L]{\hyperlink{\thechapter}{\scshape \chaptername{}~\thechapter. \quad \leftmark}}
\fancyhead[R]{\hyperlink{\thechapter-\theProblemNum}{\scshape Problem~\theProblemNum.}}

% ============ End of Class ============ %
\endinput